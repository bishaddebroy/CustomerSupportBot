import json
import os
import logging
import boto3
from botocore.exceptions import ClientError
import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE_NAME')
LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT_NAME')
EMBEDDING_ENDPOINT = os.environ.get('EMBEDDING_ENDPOINT_NAME')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize AWS clients
dynamodb = boto3.client('dynamodb', region_name=REGION)
sagemaker = boto3.client('sagemaker', region_name=REGION)

def check_dynamodb_status():
    """Check DynamoDB table status"""
    try:
        response = dynamodb.describe_table(
            TableName=DYNAMODB_TABLE
        )
        return {
            'status': response['Table']['TableStatus'],
            'error': None
        }
    except ClientError as e:
        logger.error(f"Error checking DynamoDB: {str(e)}")
        return {
            'status': 'ERROR',
            'error': str(e)
        }

def check_endpoint_status(endpoint_name):
    """Check SageMaker endpoint status"""
    try:
        response = sagemaker.describe_endpoint(
            EndpointName=endpoint_name
        )
        return {
            'status': response['EndpointStatus'],
            'error': None
        }
    except ClientError as e:
        logger.error(f"Error checking endpoint {endpoint_name}: {str(e)}")
        return {
            'status': 'ERROR',
            'error': str(e)
        }

def handle_options(event):
    """Handle OPTIONS request for CORS"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': ''
    }

def lambda_handler(event, context):
    """Lambda handler for health check API"""
    try:
        # Check if this is an OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options(event)
            
        logger.info(f"Received health check event")
        
        # Check DynamoDB table status
        dynamodb_status = check_dynamodb_status()
        
        # Check SageMaker endpoints status
        llm_status = check_endpoint_status(LLM_ENDPOINT)
        embedding_status = check_endpoint_status(EMBEDDING_ENDPOINT)
        
        # Determine overall status
        is_healthy = (
            dynamodb_status['status'] == 'ACTIVE' and 
            llm_status['status'] == 'InService' and 
            embedding_status['status'] == 'InService'
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy' if is_healthy else 'unhealthy',
                'components': {
                    'dynamodb': {
                        'status': dynamodb_status['status'],
                        'healthy': dynamodb_status['status'] == 'ACTIVE'
                    },
                    'llm_endpoint': {
                        'status': llm_status['status'],
                        'healthy': llm_status['status'] == 'InService'
                    },
                    'embedding_endpoint': {
                        'status': embedding_status['status'],
                        'healthy': embedding_status['status'] == 'InService'
                    }
                },
                'timestamp': datetime.datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            })
        }