import json
import os
import logging
import boto3
from botocore.exceptions import ClientError

# Import RAG components from shared layer
from vector_store import VectorStore
from llm_handler import LLMHandler
from rag_engine import RAGEngine

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get configuration from environment variables
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE_NAME')
LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT_NAME')
EMBEDDING_ENDPOINT = os.environ.get('EMBEDDING_ENDPOINT_NAME')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize components
vector_store = None
llm_handler = None
rag_engine = None

def initialize_components():
    """Initialize RAG components lazily to improve cold start times"""
    global vector_store, llm_handler, rag_engine
    
    if vector_store is None:
        vector_store = VectorStore(
            table_name=DYNAMODB_TABLE,
            embedding_endpoint=EMBEDDING_ENDPOINT,
            region=REGION
        )
    
    if llm_handler is None:
        llm_handler = LLMHandler(
            endpoint_name=LLM_ENDPOINT,
            region=REGION
        )
    
    if rag_engine is None:
        rag_engine = RAGEngine(llm_handler, vector_store)

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

def lambda_handler(event, context):
    """
    Lambda handler for chat API
    """
    try:
        # Check if this is an OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options(event)
        
        # Initialize components if needed
        initialize_components()
        
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '')
        session_id = body.get('session_id', 'default_session')
        
        logger.info(f"Processing message from session {session_id}: {user_message}")
        
        if not user_message:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'No message provided'
                })
            }
        
        # Process the query through RAG
        response = rag_engine.process_query(user_message, session_id)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'response': response
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        
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