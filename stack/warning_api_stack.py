"""Module Stack impl."""

import json
import pathlib

from aws_cdk import Duration, Stack, aws_apigateway
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam
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

        user_pool = cognito.UserPool(
            self,
            f"{conf.full_name}UserPool",
            user_pool_name=f"{conf.full_name}-user-pool",
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            sign_in_aliases=cognito.SignInAliases(
                email=True,
            ),
            # standard_attributes=cognito.StandardAttributes(
            #     nickname=cognito.StandardAttribute(
            #         required=True,
            #         mutable=False
            #     ),
            # ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            mfa=cognito.Mfa.OFF,
            self_sign_up_enabled=True,
        )
        # GOOGLE_CLIENT_ID

        # Enable self-registration with email confirm and required attributes
        user_pool_client = user_pool.add_client(
            f"{conf.full_name}userPoolClient",
            generate_secret=True,
            prevent_user_existence_errors=True,
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
                cognito.UserPoolClientIdentityProvider.GOOGLE,
            ],
            user_pool_client_name=f"{conf.full_name}-user-pool-client",
            auth_flows=cognito.AuthFlow(user_password=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True, implicit_code_grant=True
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=["http://localhost/login"],
                logout_urls=["http://localhost/logout"],
            ),
        )
        google_provider = cognito.UserPoolIdentityProviderGoogle(
            self,
            "Google",
            client_id=conf.GOOGLE_CLIENT_ID,
            client_secret=conf.GOOGLE_SECRET,
            user_pool=user_pool,
            scopes=["email", "profile", "openid"],
        )
        user_pool_client.node.add_dependency(google_provider)

        warning_table = aws_dynamodb.Table.from_table_name(
            self,
            f"{conf.full_name}-warning-table",
            table_name=conf.WARNINGS_TABLE,
        )

        warning_history_table = aws_dynamodb.Table.from_table_name(
            self,
            f"{conf.full_name}-warning-history-table",
            table_name=conf.WARNINGS_HISTORY_TABLE,
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
            actions=["sns:Publish"], resources=["*"]
        )
        base_lambda.add_to_role_policy(sns_publish_policy)

        ses_publish_policy = aws_iam.PolicyStatement(
            actions=["ses:SendEmail"], resources=["*"]
        )
        base_lambda.add_to_role_policy(ses_publish_policy)

        warning_table.grant_read_write_data(base_lambda)
        warning_history_table.grant_read_write_data(base_lambda)

        policy_statement = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["dynamodb:Query"],
            resources=[
                "arn:aws:dynamodb:us-east-1:323677137491:table/warnings-table/index/warning_datetime-index",
                "arn:aws:dynamodb:us-east-1:323677137491:table/warnings-table/index/user_id-index",
            ],
        )
        policy_statement2 = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["dynamodb:Query"],
            resources=[
                "arn:aws:dynamodb:us-east-1:323677137491:table/warnings_history/index/user_id-index"
            ],
        )
        base_lambda.add_to_role_policy(policy_statement)
        base_lambda.add_to_role_policy(policy_statement2)

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

        schedule_fn = lambda_.Function(
            self,
            f"{conf.full_name}-schedule_check",
            runtime=lambda_.Runtime.PYTHON_3_8,
            handler="index.handler",
            timeout=Duration.minutes(15),
            code=lambda_.Code.from_inline(
                f"""
from urllib.request import urlopen

URL = "{conf.WARNING_CHECK_URL}"
def handler(event, context):
    urlopen(URL)
"""
            ),
        )

        # Create a rule with a schedule that triggers every 5 minutes
        rule = events.Rule(
            self,
            f"{conf.full_name}-rule",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )

        rule.add_target(targets.LambdaFunction(schedule_fn))
