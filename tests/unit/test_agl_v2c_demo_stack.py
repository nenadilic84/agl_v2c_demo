import aws_cdk as core
import aws_cdk.assertions as assertions

from agl_v2c_demo.agl_v2c_demo_stack import AglV2CDemoStack

# example tests. To run these tests, uncomment this file along with the example
# resource in agl_v2c_demo/agl_v2c_demo_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AglV2CDemoStack(app, "agl-v2c-demo")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
