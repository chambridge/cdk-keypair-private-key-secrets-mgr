import datetime
import json
import secrets
from aws_cdk import (
    BundlingOptions,
    Duration,
    CfnOutput,
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    custom_resources as cr,
)
from aws_cdk.aws_ec2 import Vpc, NatProvider, SubnetConfiguration, SubnetType, SecurityGroup
from constructs import Construct


class ExampleNetworkStack(Stack):
    def __init__(self, scope: Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Subnet configurations for a public and private tier
        subnet1 = SubnetConfiguration(name="PublicNet", subnet_type=SubnetType.PUBLIC, cidr_mask=24)
        subnet2 = SubnetConfiguration(
            name="PrivateNet",
            subnet_type=SubnetType.PRIVATE_WITH_NAT,
            cidr_mask=24,
        )

        vpc = Vpc(
            self,
            "ExampleVPC",
            cidr="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            max_azs=2,
            nat_gateway_provider=NatProvider.gateway(),
            nat_gateways=1,
            subnet_configuration=[subnet1, subnet2],
        )

        # This will export the VPC's ID in CloudFormation under the key
        # 'vpcid'
        CfnOutput(self, "vpcid", value=vpc.vpc_id)

        # Prepares output attributes to be passed into other stacks
        # In this case, it is our VPC, subnets and public_subnet_id.
        self.output_props = props.copy()
        self.output_props["vpc"] = vpc
        self.output_props["subnets"] = vpc.public_subnets
        self.output_props["public_subnet_id"] = vpc.public_subnets[0].subnet_id

        policy_document = {"Version": "2012-10-17", "Statement": [{"Sid": "VisualEditor0", "Effect": "Allow", "Action": "ec2:CreateKeyPair", "Resource": "*"}]}
        custom_policy_document = iam.PolicyDocument.from_json(policy_document)

        # Create role
        ec2_lambda_role_name = "lambda-ec2-keypair-role"
        lambda_role = iam.Role(
            scope=self,
            id=ec2_lambda_role_name,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=ec2_lambda_role_name,
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
            ],
            inline_policies={f"{ec2_lambda_role_name}-keypair-policy": custom_policy_document},
        )

        lambda_sg_name = "ec2-keypair-lambda-sg"
        lambda_sg = SecurityGroup(self, lambda_sg_name, security_group_name=lambda_sg_name, vpc=vpc, allow_all_outbound=True)

        # Defines an AWS Lambda resource for EC2 Keypair
        lambda_name = "ec2-keypair-init"
        ec2_keypair_init = _lambda.Function(
            self,
            lambda_name,
            runtime=_lambda.Runtime.PYTHON_3_9,
            function_name=lambda_name,
            description="Lambda function deployed to initialize the EC2 Keypair used",
            code=_lambda.Code.from_asset(
                "./keypair_manager/lambda",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_9.bundling_image,
                    command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"],
                ),
            ),
            handler="ec2_keypair_init.handler",
            role=lambda_role,
            security_groups=[lambda_sg],
            timeout=Duration.minutes(10),
            vpc=vpc,
        )

        randomizer = secrets.token_urlsafe(6)
        keypair_name = f"keypair-{randomizer}"
        keypair_secret_name = f"ec2-ssh-key/{keypair_name}/private"
        ec2_keypair_dict = {"keypair_name": keypair_name, "keypair_secret_name": keypair_secret_name}
        lambda_payload = json.dumps({"params": ec2_keypair_dict})
        lambda_sdk_call_name = "{id}-ec2-keypair-init-sdk-call".format(id=datetime.datetime.now())
        lambda_sdk_params = {"FunctionName": ec2_keypair_init.function_name, "Payload": lambda_payload}
        lambda_sdk_call = cr.AwsSdkCall(
            service="Lambda", action="invoke", parameters=lambda_sdk_params, physical_resource_id=cr.PhysicalResourceId.of(lambda_sdk_call_name)
        )
        lambda_cr_name = "ec2-keypair-init-trigger"
        lambda_cr = cr.AwsCustomResource(
            self,
            lambda_cr_name,
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [iam.PolicyStatement(actions=["lambda:InvokeFunction"], effect=iam.Effect.ALLOW, resources=[ec2_keypair_init.function_arn])]
            ),
            timeout=Duration.minutes(10),
            on_create=lambda_sdk_call,
            on_update=lambda_sdk_call,
            role=lambda_role,
        )
        self.output_props.update(ec2_keypair_dict)

    @property
    def outputs(self):
        return self.output_props
