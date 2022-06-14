import boto3
import json


def create_keypair(keypair_name):
    ec2 = boto3.client("ec2")
    keypair = ec2.create_key_pair(KeyName=keypair_name)
    pem = keypair["KeyMaterial"]
    return pem


def store_privatekey(keypair_secret_name, pem):
    client = boto3.client("secretsmanager")
    secret = client.create_secret(Name=keypair_secret_name, SecretString=pem)
    return secret


def handler(event, context):
    params = event.get("params")
    keypair_name = params.get("keypair_name")
    keypair_secret_name = params.get("keypair_secret_name")
    pem = create_keypair(keypair_name)
    secret = store_privatekey(keypair_secret_name, pem)
    event["keypair_name"] = keypair_name
    event["keypair_secret_name"] = secret["Name"]
    return {"keypair_name": keypair_name, "keypair_secret_name": secret["Name"]}
