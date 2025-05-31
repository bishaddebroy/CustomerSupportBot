import logging
import boto3
import json
import time
from botocore.exceptions import ClientError

class LLMHandler:
    """
    Handler for DistilBERT QA model interactions on AWS SageMaker
    """
    
    def __init__(self, endpoint_name, region='us-east-1'):
        """
        Initialize the LLM handler
        
        Args:
            endpoint_name: SageMaker endpoint name
            region: AWS region
        """
        self.endpoint_name = endpoint_name
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS SDK clients
        self.sagemaker_runtime = boto3.client('runtime.sagemaker', region_name=region)
        
        self.logger.info(f"LLM Handler initialized with endpoint: {endpoint_name}")
    
    def generate(self, question, context, max_retries=3):
        """
        Generate answer using the SageMaker endpoint
        
        Args:
            question: The question to answer
            context: The context containing the answer
            max_retries: Maximum number of retries for API calls
            
        Returns:
            Generated answer from DistilBERT QA model
        """
        # Format as list [question, context] as required by the model
        payload = [question, context]
        
        # Convert the payload to JSON
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Call the SageMaker endpoint with retries
        retries = 0
        while retries <= max_retries:
            try:
                self.logger.debug(f"Sending request to SageMaker endpoint: {self.endpoint_name}")
                start_time = time.time()
                
                response = self.sagemaker_runtime.invoke_endpoint(
                    EndpointName=self.endpoint_name,
                    ContentType='application/list-text',  # Use the content type from your example
                    Body=payload_bytes
                )
                
                # Log the inference time
                inference_time = time.time() - start_time
                self.logger.info(f"LLM inference completed in {inference_time:.2f} seconds")
                
                # Parse the response - extract the 'answer' field as shown in your example
                response_body = response['Body'].read().decode('utf-8')
                response_json = json.loads(response_body)
                
                # Extract the answer based on the model's output format
                if isinstance(response_json, dict) and 'answer' in response_json:
                    return response_json['answer']
                else:
                    return str(response_json)
                
            except ClientError as e:
                retries += 1
                error_code = e.response.get('Error', {}).get('Code')
                
                # Handle specific error types
                if error_code == 'ModelError':
                    self.logger.error(f"Model error: {str(e)}")
                    return "I'm sorry, I encountered an issue processing your request."
                    
                elif error_code == 'ThrottlingException':
                    # Exponential backoff for throttling
                    wait_time = 2 ** retries
                    self.logger.warning(f"Throttling detected, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    
                else:
                    if retries >= max_retries:
                        self.logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        return "I'm sorry, I'm having trouble connecting to my knowledge base right now."
                    
                    # General retry with backoff
                    wait_time = 1 * retries
                    self.logger.warning(f"Error calling endpoint, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"Unexpected error in LLM generation: {str(e)}", exc_info=True)
                return "I'm sorry, an unexpected error occurred while processing your request."