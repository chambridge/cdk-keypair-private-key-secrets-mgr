from aws_cdk.aws_ec2 import SubnetType
from aws_cdk import (
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    Stack,
    aws_iam as iam,
)
from constructs import Construct
from . import AWS_KEYPAIR, AWS_AMI, AWS_REGION

import secrets


class KeypairManagerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        userdata_file = open("./bootstrap_manager_node.sh", "rb").read()
        userdata = ec2.UserData.for_linux()
        userdata.add_commands("export ASG_NAME={0}".format(props["asg_name"]))
        userdata.add_commands("export KEYPAIR_SECRET_NAME={0}".format(props["keypair_secret_name"]))
        userdata.add_commands(str(userdata_file, "utf-8"))

        installer_ec2_role = iam.Role(
            self,
            "manager-instance-role",
            assumed_by=iam.CompositePrincipal(iam.ServicePrincipal("ec2.amazonaws.com"), iam.ServicePrincipal("ssm.amazonaws.com")),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ReadOnlyAccess"),
            ],
        )

        # Management System Exposed publically on SSH
        installer_instance = ec2.Instance(
            self,
            "kepair_manager",
            vpc=props["vpc"],
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.XLARGE),
            machine_image=ec2.MachineImage.generic_linux({AWS_REGION: AWS_AMI}),
            key_name="{keypair}".format(keypair=AWS_KEYPAIR),
            vpc_subnets=ec2.SubnetSelection(subnet_type=SubnetType.PUBLIC),
            user_data=userdata,
            role=installer_ec2_role,
        )

        sg_manager = ec2.SecurityGroup(self, id="sg_manager", vpc=props["vpc"], security_group_name="sg_manager")

        # Allow SSH connection to installer
        sg_manager.connections.allow_from(sg_manager, ec2.Port.tcp(22), "SSH Ingress")

        # Adds the security group 'sg_manager' to installer instance
        installer_instance.add_security_group(sg_manager)
