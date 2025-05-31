import json
import os
import logging
import boto3
import uuid
import base64
import binascii
import re
from io import BytesIO

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration from environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

def get_content_type(file_extension):
    """Determine content type based on file extension"""
    content_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword'
    }
    return content_types.get(file_extension.lower(), 'application/octet-stream')

def handle_options(event):
    """Handle OPTIONS request for CORS"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': ''
    }

def is_base64(s):
    """Check if a string is base64 encoded"""
    # Base64 strings use only A-Z, a-z, 0-9, +, /, and = for padding
    pattern = r'^[A-Za-z0-9+/]+={0,2}$'
    return bool(re.match(pattern, s))

def lambda_handler(event, context):
    """Lambda handler for document upload API"""
    try:
        # Check if this is an OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options(event)
            
        logger.info(f"Received upload event")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Check if file data is provided
        if not body.get('file') or not body.get('filename'):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'No file data provided'
                })
            }
        
        # Get file data and filename
        file_data_input = body['file']
        
        # Check if the input is already base64 encoded
        if is_base64(file_data_input):
            # Handle as base64
            try:
                # Fix padding if needed
                missing_padding = len(file_data_input) % 4
                if missing_padding:
                    file_data_input += '=' * (4 - missing_padding)
                
                file_data = base64.b64decode(file_data_input)
            except binascii.Error as e:
                logger.error(f"Base64 decoding error: {str(e)}")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'error': f'Invalid base64 data: {str(e)}'
                    })
                }
        else:
            # Treat as raw text - convert to bytes
            file_data = file_data_input.encode('utf-8')
        
        filename = body['filename']
        file_extension = os.path.splitext(filename)[1].lower()
        
        # If no extension provided and treating as raw text, default to .txt
        if not file_extension:
            filename += '.txt'
            file_extension = '.txt'
        
        # Validate file type
        valid_types = ['.pdf', '.txt', '.docx', '.doc']
        if file_extension not in valid_types:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Invalid file type. Supported types: PDF, TXT, DOCX, DOC'
                })
            }
        
        # Generate a unique filename
        document_id = str(uuid.uuid4())
        s3_key = f"documents/{document_id}/{filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_data,
            ContentType=get_content_type(file_extension),
            Metadata={
                'document-id': document_id,
                'original-filename': filename
            }
        )
        
        logger.info(f"File uploaded to s3://{S3_BUCKET}/{s3_key}")
        
        # The S3 event will trigger the document-processor Lambda automatically
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'documentId': document_id,
                'message': f'Document {filename} uploaded successfully and processing has started'
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }