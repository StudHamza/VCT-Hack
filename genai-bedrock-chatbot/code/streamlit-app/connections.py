import os
import boto3

from botocore.config import Config


class Connections:
    region_name = 'us-east-1' #os.environ["AWS_REGION"]
    lambda_function_name = 'chat-assistant-stack-chat-lambda' #os.environ["LAMBDA_FUNCTION_NAME"]
    log_level = 'DEBUG' #os.environ["LOG_LEVEL"]

    lambda_client = boto3.client(
        "lambda",
        region_name=region_name,
        config=Config(read_timeout=300, connect_timeout=300),
    )
