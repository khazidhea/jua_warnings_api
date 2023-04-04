"""Module Stack impl."""

import json
import pathlib

from aws_cdk import Duration, Stack, aws_apigateway, aws_dynamodb, aws_iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs
from constructs import Construct

from config import GlobalConfig

# pylint: disable=[line-too-long, too-many-locals]

ACCESS_LOG_FORMAT = aws_apigateway.AccessLogFormat.custom(
    json.dumps(
        {
            "requestId": "$context.requestId",
            "extendedRequestId": "$context.extendedRequestId",
            "ip": "$context.identity.sourceIp",
            "caller": "$context.identity.caller",
            "user": "$context.identity.user",
            "requestTime": "$context.requestTime",
            "httpMethod": "$context.httpMethod",
            "resourcePath": "$context.resourcePath",
            "status": "$context.status",
            "protocol": "$context.protocol",
            "responseLength": "$context.responseLength",
            "apiKey": "$context.identity.apiKey",
            "path": "$context.path",
            "stage": "$context.stage",
        }
    )
)


class WarningApiStack(Stack):
    """The WarningApiStack stack"""

    def __init__(self, scope: Construct, conf: GlobalConfig, **kwargs) -> None:
        """init the WarningApiStack stack"""

        super().__init__(scope, conf.full_name, **kwargs)

        warning_table = aws_dynamodb.Table.from_table_name(
            self,
            f"{conf.full_name}-warning-table",
            table_name=conf.WARNINGS_TABLE,
        )

        app_root_path = "/" if conf.is_prod or conf.is_stage else "/dev"
        base_lambda = lambda_.DockerImageFunction(
            self,
            f"{conf.full_name}",
            code=lambda_.DockerImageCode.from_image_asset(
                pathlib.Path.cwd().as_posix()
            ),
            timeout=Duration.minutes(2),
            memory_size=4096,
            environment={
                "STAGE": conf.STAGE,
                "LOG_LEVEL": conf.LOG_LEVEL,
                "SENTRY_DSN": conf.SENTRY_DSN,
                "APP_ROOT_PATH": app_root_path,
            },
        )

        # Add permissions for lambda
        sns_publish_policy = aws_iam.PolicyStatement(
            actions=["sns:Publish"],
            resources=["*"]
        )
        base_lambda.add_to_role_policy(sns_publish_policy)

        ses_publish_policy = aws_iam.PolicyStatement(
            actions=["ses:SendEmail"],
            resources=["*"]
        )
        base_lambda.add_to_role_policy(ses_publish_policy)

        warning_table.grant_read_write_data(base_lambda)

        policy_statement = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["dynamodb:Query"],
            resources=[
                "arn:aws:dynamodb:us-east-1:323677137491:table/warnings-table/index/warning_datetime-index"
            ],
        )
        base_lambda.add_to_role_policy(policy_statement)

        # Access logs, including API key
        access_log_group = aws_logs.LogGroup(self, f"{conf.full_name}-access-log")
        access_log_destination = aws_apigateway.LogGroupLogDestination(access_log_group)

        deployment_stage = aws_apigateway.StageOptions(
            stage_name="dev",
            logging_level=aws_apigateway.MethodLoggingLevel.INFO,
            access_log_destination=access_log_destination,
            access_log_format=ACCESS_LOG_FORMAT,
        )

        integration = aws_apigateway.LambdaIntegration(base_lambda, proxy=True)

        api = aws_apigateway.RestApi(
            self,
            f"{conf.full_name}-proxy",
            deploy_options=deployment_stage,
            minimum_compression_size=25 * 1024,  # 25KB
            cloud_watch_role=True,
            binary_media_types=["*/*"],
            default_integration=integration,
        )

        docs = api.root.add_resource("docs")
        docs.add_method("ANY", integration=integration)
        docs.add_proxy(
            default_integration=integration,
            any_method=True,
            default_method_options={"api_key_required": False},
        )

        static = api.root.add_resource("static")
        static.add_method("ANY", integration=integration)
        static.add_proxy(
            default_integration=integration,
            any_method=True,
            default_method_options={"api_key_required": False},
        )

        api.root.add_proxy(
            default_integration=integration,
            any_method=True,
            default_method_options={"api_key_required": False},
        )
