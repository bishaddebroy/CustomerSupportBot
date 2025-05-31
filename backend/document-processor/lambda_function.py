import json
import os
import boto3
import uuid
import logging
import urllib.parse
from io import BytesIO
import base64
import time
from decimal import Decimal

# Import shared libraries from Lambda layer
from vector_store import VectorStore
from text_processing import extract_text, split_text_into_chunks

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sagemaker_runtime = boto3.client('runtime.sagemaker')

# Configuration from environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE_NAME')
EMBEDDING_ENDPOINT = os.environ.get('EMBEDDING_ENDPOINT_NAME')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize vector store
vector_store = VectorStore(
    table_name=DYNAMODB_TABLE,
    embedding_endpoint=EMBEDDING_ENDPOINT,
    region=REGION
)

def lambda_handler(event, context):
    """
    Lambda function triggered by S3 events to process documents
    and store them in the vector database
    """
    try:
        logger.info("Received event: " + json.dumps(event))
        
        # Get bucket name and file key from the S3 event
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        logger.info(f"Processing file {file_key} from bucket {bucket_name}")
        
        # Generate a unique document ID
        document_id = str(uuid.uuid4())
        
        # Download the file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read()
        
        # Extract file extension
        file_extension = os.path.splitext(file_key)[1].lower()
        
        # Extract text based on file type
        text = extract_text(file_content, file_extension)
        
        # Additional cleaning to ensure no invalid characters
        text = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in text)
        
        if not text:
            logger.warning(f"No text extracted from {file_key}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'message': 'No text could be extracted from the document'
                })
            }
        
        # Get document metadata
        metadata = {
            'source': file_key,
            'file_type': file_extension,
            'document_id': document_id,
            'bucket': bucket_name,
            'processed_at': time.time()
        }
        
        # Convert any float values in metadata to Decimal for DynamoDB compatibility
        processed_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, float):
                processed_metadata[key] = Decimal(str(value))
            else:
                processed_metadata[key] = value
        
        # Split text into chunks
        chunks = split_text_into_chunks(text)
        logger.info(f"Document split into {len(chunks)} chunks")
        
        # Add each chunk to the vector store
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_metadata = processed_metadata.copy()
            chunk_metadata['chunk_index'] = i
            
            # Add to vector store
            success = vector_store.add_document(
                document_id=chunk_id,
                content=chunk,
                metadata=chunk_metadata
            )
            
            if not success:
                logger.error(f"Failed to add chunk {i} to vector store")
        
        logger.info(f"Successfully processed document {document_id} with {len(chunks)} chunks")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'document_id': document_id,
                'chunks_processed': len(chunks)
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }