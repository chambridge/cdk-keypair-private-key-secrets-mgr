from aws_cdk.aws_ec2 import SubnetType
from aws_cdk import (
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
    Stack,
    aws_iam as iam,
)
from constructs import Construct
from . import AWS_AMI, AWS_REGION


class ExampleSystemStack(Stack):
    def __init__(self, scope: Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Autoscale group
        autoscale_group = autoscaling.AutoScalingGroup(
            self,
            "example-autoscale-group",
            vpc=props["vpc"],
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.MEMORY5, ec2.InstanceSize.XLARGE),
            machine_image=ec2.MachineImage.generic_linux({AWS_REGION: AWS_AMI}),
            key_name="{keypair}".format(keypair=props["keypair_name"]),
            vpc_subnets=ec2.SubnetSelection(subnet_type=SubnetType.PRIVATE_WITH_NAT),
        )

        asg_dict = {
            "asg_name": autoscale_group.auto_scaling_group_name,
        }
        props.update(asg_dict)

        # Creates a security group for the autoscale group
        sg_example_asg = ec2.SecurityGroup(self, id="sg_example_asg", vpc=props["vpc"], security_group_name="sg_example_asg")

        # Creates a security group for the the autoscale group application load balancer
        sg_alb = ec2.SecurityGroup(self, id="sg_alb", vpc=props["vpc"], security_group_name="sg_example_asg_alb")

        # Allow all egress from ALB to ASG instance
        sg_alb.connections.allow_to(sg_example_asg, ec2.Port.all_tcp(), "To ASG")

        # Allows connections from ALB to ASG instances access port 80
        # where application UI listens
        sg_example_asg.connections.allow_from(sg_alb, ec2.Port.tcp(80), "ALB Ingress")

        # Allow SSH connection between manager and auto-scale group
        sg_example_asg.connections.allow_from(sg_example_asg, ec2.Port.tcp(22), "SSH Ingress")

        sg_example_asg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="ssh",
        )

        # Adds the security group 'sg_example_asg' to the autoscaling group
        autoscale_group.add_security_group(sg_example_asg)

        # Creates an application load balance
        example_alb = elbv2.ApplicationLoadBalancer(
            self,
            "ExampleALB",
            vpc=props["vpc"],
            security_group=sg_alb,
            internet_facing=True,
        )

        # Adds the autoscaling group's instance to be registered as targets on port 80
        example_listener = example_alb.add_listener("Listener", port=80)
        example_listener.add_targets("Target", port=80, protocol=elbv2.ApplicationProtocol.HTTP, targets=[autoscale_group])

        # This creates a "0.0.0.0/0" rule to allow every one to access the ALB
        example_listener.connections.allow_default_port_from_any_ipv4("Open to the world")
