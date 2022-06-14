#!/usr/bin/env python3
import os

import aws_cdk as cdk
from keypair_manager.net import ExampleNetworkStack
from keypair_manager.systems import ExampleSystemStack
from keypair_manager.manager import KeypairManagerStack


app = cdk.App()
props = {}
en_stack = ExampleNetworkStack(app, "ExampleNetworkStack", props)

es_stack = ExampleSystemStack(app, "ExampleSystemStack", en_stack.outputs)
es_stack.add_dependency(en_stack)

km_stack = KeypairManagerStack(app, "KeypairManagerStack", en_stack.outputs)
km_stack.add_dependency(en_stack)

app.synth()
