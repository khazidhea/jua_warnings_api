"""Module create/update aws cloudFormation stack."""
#!/usr/bin/env python3
import aws_cdk as cdk

from config import GlobalConfig
from stack.warning_api_stack import WarningApiStack

conf = GlobalConfig()

app = cdk.App()
stack = WarningApiStack(
    app,
    conf,
)

cdk.Tags.of(stack).add("project", conf.APP_NAME)
cdk.Tags.of(stack).add("stage", conf.STAGE)

app.synth()
