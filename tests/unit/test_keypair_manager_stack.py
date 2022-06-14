import aws_cdk as core
import aws_cdk.assertions as assertions

from keypair_manager.manager import KeypairManagerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in temp/temp_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = KeypairManagerStack(app, "keypair_manager")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
