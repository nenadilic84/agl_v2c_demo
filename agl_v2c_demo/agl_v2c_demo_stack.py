from aws_cdk import (
    Stack,
    CfnOutput,
    aws_lambda as lambda_,
    aws_iot as iot,
    aws_timestream as timestream,
    aws_iam as iam,
    CfnOutput
)

from constructs import Construct

class AglV2CDemoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the Lambda layer for Python dependencies
        lambda_layer = lambda_.LayerVersion(self, "PythonDependenciesLayer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            code=lambda_.Code.from_asset("lambda", bundling={
                "command": [
                    "/bin/bash",
                    "-c",
                    "python3 -m pip install -r requirements.txt --no-cache-dir -t /asset-output/python --index-url https://pypi.org/simple/"
                ],
                "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                "platform": "linux/amd64"
            })
        )

        # Define the Lambda function
        lambda_function = lambda_.Function(
            self, "IoTMessageHandler",
            description="Processes IoT messages and stores them in Timestream",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("lambda", bundling={
                "image": lambda_.Runtime.PYTHON_3_11.bundling_image,
                "command": [
                    "/bin/bash",
                    "-c",
                    "cp -a *.py /asset-output"
                ],
                "platform": "linux/amd64"
            }),
            layers=[lambda_layer],
            handler="lambda_handler.handler",
            # timeout=Duration.minutes(10),
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "TIMESTREAM_DATABASE_NAME": "IoTMessages",
                "TIMESTREAM_TABLE_NAME": "IoTMessagesTable"
            }
        )

        # Define the IoT topic rule
        topic_rule = iot.CfnTopicRule(self, "IoTTopicRule",
            topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
                aws_iot_sql_version="2016-03-23",
                sql="SELECT encode(*, 'base64') AS payload FROM 'agl/v2c/demo'",
                actions=[
                    iot.CfnTopicRule.ActionProperty(
                        lambda_=iot.CfnTopicRule.LambdaActionProperty(
                            function_arn=lambda_function.function_arn
                        )
                    )
                ]
            )
        )

        # Grant IoT permission to invoke the Lambda function
        lambda_function.add_permission(
            "IoTInvokeLambda",
            principal=iam.ServicePrincipal("iot.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=topic_rule.attr_arn
        )


        # Define the Timestream database
        database = timestream.CfnDatabase(self, "IoTMessagesDatabase",
            database_name="IoTMessages"
        )

        # Define the Timestream table
        table = timestream.CfnTable(self, "IoTMessagesTable",
            database_name=database.ref,
            table_name="IoTMessagesTable",
            retention_properties={
                "memoryStoreRetentionPeriodInHours": "24",
                "magneticStoreRetentionPeriodInDays": "7"
            }
        )

        role = iam.Role(
            self,
            "AmazonGrafanaServiceRoleAGLV2CDemo",
            assumed_by=iam.ServicePrincipal("grafana.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonTimestreamReadOnlyAccess")
            ]
        )

        CfnOutput(self, "RoleAwsAccountId", value=self.account)
        CfnOutput(self, "RoleAwsRegion", value=self.region)
        CfnOutput(self, "WorkspaceRoleToAssume", value=role.role_arn)

        