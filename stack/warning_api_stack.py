"""Module Stack impl."""

import json
import pathlib
import time

from aws_cdk import Duration, Stack, aws_apigateway
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs, aws_s3
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

        # One bronze bucket for all stages
        bucket = aws_s3.Bucket.from_bucket_arn(
            self, "BucketByArn", "arn:aws:s3:::bronze-data-platform-prod"
        )

        # One DynamoDB table for all stages
        forecast_table = aws_dynamodb.Table.from_table_name(
            self,
            f"{conf.full_name}-table",
            table_name="forecast-releases-prod",
        )

        warnings_table = aws_dynamodb.Table(
            self,
            f"{conf.full_name}-table",
            partition_key=aws_dynamodb.Attribute(
                name="id", type=aws_dynamodb.AttributeType.STRING
            ),
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
                "DYNAMODB_FORECAST_TABLE": forecast_table.table_name,
                "WARNINGS_TABLE": warnings_table.table_name,
            },
        )

        # Add permissions for lambda
        bucket.grant_read(base_lambda)
        forecast_table.grant_read_data(base_lambda)
        warnings_table.grant_read_data(base_lambda)

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

        # api_key = api.add_api_key(f"{conf.full_name}-api-key")
        # usage_plan = api.add_usage_plan(
        #     f"{conf.full_name}-add-usage-plan",
        # )
        # usage_plan.add_api_stage(api=api, stage=api.deployment_stage)
        # usage_plan.add_api_key(api_key)
