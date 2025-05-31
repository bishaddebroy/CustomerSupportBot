import logging
import boto3
import json
import time
import uuid
from botocore.exceptions import ClientError
from decimal import Decimal

class VectorStore:
    """
    Vector database implementation using Amazon DynamoDB and custom similarity search
    """
    
    def __init__(self, table_name, embedding_endpoint, region='us-east-1'):
        """
        Initialize the vector store
        
        Args:
            table_name: DynamoDB table name
            embedding_endpoint: SageMaker endpoint name for embeddings
            region: AWS region
        """
        self.table_name = table_name
        self.embedding_endpoint = embedding_endpoint
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS SDK clients
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=region)
        
        # Connect to the DynamoDB table
        self.table = self.dynamodb.Table(table_name)
        
        self.logger.info(f"Vector store initialized with table: {table_name}")
        
    def add_document(self, document_id, content, metadata=None, embedding=None):
        """
        Add a document to the vector store
        
        Args:
            document_id: Unique identifier for the document
            content: Text content of the document
            metadata: Additional metadata for the document
            embedding: Pre-computed embedding vector (optional)
            
        Returns:
            Boolean indicating success
        """
        try:
            # Generate embedding if not provided
            if embedding is None:
                embedding = self.generate_embedding(content)
            
            # Convert embedding to DynamoDB-compatible format (Decimal)
            embedding_decimal = [Decimal(str(x)) for x in embedding]
            
            # Create metadata if not provided
            if metadata is None:
                metadata = {}
                
            # Convert any float values in metadata to Decimal for DynamoDB compatibility
            processed_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, float):
                    processed_metadata[key] = Decimal(str(value))
                elif isinstance(value, dict):
                    # Handle nested dictionaries
                    processed_value = {}
                    for k, v in value.items():
                        if isinstance(v, float):
                            processed_value[k] = Decimal(str(v))
                        else:
                            processed_value[k] = v
                    processed_metadata[key] = processed_value
                elif isinstance(value, list):
                    # Handle lists of values
                    processed_value = []
                    for v in value:
                        if isinstance(v, float):
                            processed_value.append(Decimal(str(v)))
                        else:
                            processed_value.append(v)
                    processed_metadata[key] = processed_value
                else:
                    processed_metadata[key] = value
                    
            # Add timestamp
            processed_metadata['timestamp'] = Decimal(str(time.time()))
                
            # Prepare item for DynamoDB
            item = {
                'id': document_id,
                'content': content,
                'metadata': processed_metadata,
                'embedding': embedding_decimal
            }
            
            # Store in DynamoDB
            self.table.put_item(Item=item)
            
            self.logger.info(f"Added document {document_id} to vector store")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding document to vector store: {str(e)}", exc_info=True)
            return False
    
    def generate_embedding(self, text):
        """
        Generate embedding for text using SageMaker endpoint
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            # Format as a list with a single text entry
            text_list = [text]
            
            # Convert to JSON and encode as UTF-8
            payload_bytes = json.dumps(text_list).encode('utf-8')
            
            # Log the payload for debugging
            self.logger.info(f"Sending embedding request with payload format: list with single text entry")
            
            # Call SageMaker endpoint with the correct content type
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=self.embedding_endpoint,
                ContentType='application/x-text',  # This is the content type your model expects
                Body=payload_bytes
            )
            
            # Parse response
            response_body = response['Body'].read().decode('utf-8')
            
            # Log the FULL response for debugging
            self.logger.info(f"Received raw embedding response: {response_body}")
            
            # Try to parse the response
            try:
                # First attempt to parse as JSON
                embedding = json.loads(response_body)
                
                # Log detailed info about the embedding structure
                if isinstance(embedding, list):
                    self.logger.info(f"Embedding is a list of length {len(embedding)}")
                    if len(embedding) > 0:
                        self.logger.info(f"First element type: {type(embedding[0])}")
                elif isinstance(embedding, dict):
                    self.logger.info(f"Embedding is a dict with keys: {embedding.keys()}")
                else:
                    self.logger.info(f"Embedding is type: {type(embedding)}")
                
                # Handle common embedding formats based on structure
                if isinstance(embedding, list):
                    # If it's a list of lists (batch format) but we only sent one text
                    if len(embedding) > 0 and isinstance(embedding[0], list):
                        return embedding[0]
                    # If it's directly a vector
                    elif len(embedding) > 0 and isinstance(embedding[0], (int, float, str)):
                        return [float(x) for x in embedding]  # Convert any string numbers to float
                elif isinstance(embedding, dict):
                    # Extract from dict format {"embedding": [...]}
                    if "embedding" in embedding and isinstance(embedding["embedding"], list):
                        return embedding["embedding"]
                    # Try other common dict keys
                    for key in ["embeddings", "vector", "vectors", "value", "values"]:
                        if key in embedding and isinstance(embedding[key], list):
                            return embedding[key]
                
                # If we couldn't determine format, log error and return the entire response
                self.logger.error(f"Could not determine embedding format from: {response_body[:200]}...")
                
                # If it's a list, return it directly as last resort
                if isinstance(embedding, list) and len(embedding) > 0:
                    self.logger.info("Returning full embedding list as fallback")
                    return embedding
                    
                # Default fallback
                return [0.0] * 384
                
            except json.JSONDecodeError:
                # Not JSON, try to parse as raw text (comma or space separated values)
                self.logger.info("Response is not JSON, trying to parse as raw values")
                
                # Remove any brackets if present
                clean_text = response_body.strip()
                if clean_text.startswith('[') and clean_text.endswith(']'):
                    clean_text = clean_text[1:-1]
                    
                # Try comma-separated first
                if ',' in clean_text:
                    values = [v.strip() for v in clean_text.split(',')]
                    return [float(v) for v in values if v and not v.isspace()]
                # Then try space-separated
                else:
                    values = [v.strip() for v in clean_text.split()]
                    return [float(v) for v in values if v and not v.isspace()]
                
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
            # Return zero vector as fallback
            return [0.0] * 384
    
    def search(self, query, top_k=3):
        """
        Search for similar documents
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of dictionaries with content and metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)
            
            # Scan all items from DynamoDB
            # Note: For production systems with large data, this is inefficient
            # A service like OpenSearch would be more appropriate
            response = self.table.scan()
            items = response.get('Items', [])
            
            # Calculate similarity scores
            results = []
            for item in items:
                # Convert DynamoDB Decimal back to float for calculations
                item_embedding = [float(x) for x in item.get('embedding', [])]
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, item_embedding)
                
                results.append({
                    'id': item.get('id'),
                    'content': item.get('content'),
                    'metadata': item.get('metadata', {}),
                    'similarity': similarity
                })
            
            # Sort by similarity score (descending)
            results = sorted(results, key=lambda x: x['similarity'], reverse=True)
            
            # Return top k results
            return results[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error searching vector store: {str(e)}", exc_info=True)
            return []
    
    def _cosine_similarity(self, vec1, vec2):
        """
        Calculate cosine similarity without NumPy
        """
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
            
        return dot_product / (magnitude1 * magnitude2)
    
    def delete_document(self, document_id):
        """
        Delete a document from the vector store
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            Boolean indicating success
        """
        try:
            self.table.delete_item(Key={'id': document_id})
            self.logger.info(f"Deleted document {document_id} from vector store")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting document: {str(e)}", exc_info=True)
            return False