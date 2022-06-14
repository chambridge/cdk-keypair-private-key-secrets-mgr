#!/bin/bash -xe

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

dnf install -y nfs-utils zip unzip jq
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
export KEYPAIR_PEM=$(aws secretsmanager get-secret-value --secret-id $KEYPAIR_SECRET_NAME --region $AWS_REGION | jq -r '.SecretString')
mkdir /etc/keys

echo "-----BEGIN RSA PRIVATE KEY-----" > /etc/keys/connect.pem
echo ${KEYPAIR_PEM} | cut -c 33- | rev | cut -c 31- | rev >> /etc/keys/connect.pem
echo "-----END RSA PRIVATE KEY-----" >> /etc/keys/connect.pem

chmod 400 /etc/keys/connect.pem
chown ec2-user:ec2-user /etc/keys/connect.pem
