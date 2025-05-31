# Customer Support Bot with RAG

A cloud-based customer support chatbot that uses Custom LLM and Embedding Models with Retrieval-Augmented Generation (RAG) to provide accurate, contextual responses based on your organization's knowledge base. Built on AWS Cloud services, this solution enhances customer support capabilities by automating responses while maintaining accuracy and relevance.

## Project Overview

This application provides automated, contextually accurate responses to customer inquiries across multiple languages. It leverages a RAG architecture that grounds responses in your company's specific knowledge by retrieving relevant information before generating answers.

Key benefits:
- **Reduced Support Costs**: Automates 60-80% of common inquiries
- **24/7 Availability**: Provides instant responses regardless of time zone
- **Multilingual Support**: Serves global customers without requiring multilingual staff
- **Consistent Quality**: Ensures uniform responses based on approved knowledge
- **Scalability**: Automatically handles traffic spikes without service degradation

## Architecture

This solution uses a hybrid architecture combining serverless functions with container-based services for optimal performance and cost-efficiency:

1. **Frontend**: Static HTML/CSS/JS website hosted on S3
2. **API Layer**: API Gateway for secure endpoint management
3. **Document Processing**: Lambda functions for document ingestion and chunking
4. **Vector Storage**: DynamoDB for efficient storage and retrieval of embeddings
5. **LLM Integration**: SageMaker for hosting the language model
6. **Monitoring**: CloudWatch for comprehensive system visibility

The system implements a RAG pattern with a clear data flow:
1. Users interact with the web application
2. Queries trigger vector search in DynamoDB
3. Relevant document chunks are retrieved
4. The language model generates contextually relevant responses

## Technologies Used

- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Backend**: Python, Lambda functions
- **Database**: DynamoDB
- **Storage**: Amazon S3
- **AI/ML**: Amazon SageMaker, Custom embedding models
- **API**: Amazon API Gateway
- **Infrastructure**: AWS Lambda, S3, CloudWatch

## Features

- **Conversational Interface**: Natural language interactions with context awareness
- **Document Ingestion**: Support for PDF, TXT, DOCX formats
- **Vector Search**: Semantic search capabilities for accurate retrieval
- **Response Generation**: Natural language responses based on retrieved information
- **Simple File Upload**: Browser-based document uploading for knowledge base maintenance

## Setup Instructions

### Prerequisites
- AWS Account with appropriate permissions
- AWS Management Console access
- Python 3.9+
- Basic understanding of AWS services

### Deployment Steps

1. **Clone the repository**
   ```
   git clone https://github.com/bishaddebroy/CustomerSupportBot.git
   cd CustomerSupportBot
   ```

2. **Prepare Lambda Layers**
   ```
   # Create a directory for the layer contents
   mkdir -p shared-layer/python
   
   # Install required dependencies
   pip install -r requirements.txt -t shared-layer/python
   
   # Create ZIP file for Lambda layer
   cd lambda-layer
   zip -r ../shared-layer.zip python/
   cd ..
   ```

3. **Upload Lambda Layer to S3**
   - Sign in to AWS Management Console
   - Navigate to S3 service
   - Create a bucket for your project files or use an existing one
   - Upload the lambda-layer.zip file

4. **Deploy Frontend**
   ```
   # Upload frontend files to S3
   aws s3 sync ./frontend/ s3://your-frontend-bucket-name/ --acl public-read
   ```
   - Alternatively, manually upload files through the AWS Console
   - Enable static website hosting on the S3 bucket

5. **Manual AWS Service Setup**
   - Create Lambda functions for upload, document processing, and chat
   - Create DynamoDB table for vector store
   - Set up API Gateway endpoints
   - Deploy SageMaker endpoints for embedding and LLM models
   - Configure S3 event triggers
   - Set up necessary IAM roles and permissions

## Usage Examples

### Adding Documents to the Knowledge Base
1. Access the admin interface
2. Select "Upload Documents"
3. Choose files (PDF, DOCX, TXT supported)
4. Documents are automatically processed and added to the vector store

### Querying the System
1. Type a question in any supported language
2. The system retrieves relevant information from the knowledge base
3. A contextually accurate response is generated based on the retrieved information
4. The response is presented in the same language as the query

## Challenges and Solutions

### Encoding Issues
- **Challenge**: File uploads with different encoding formats caused processing errors
- **Solution**: Implemented robust encoding detection and character normalization

### Base64 Handling
- **Challenge**: Inconsistent base64 encoding in file uploads led to decoding errors
- **Solution**: Enhanced upload Lambda with intelligent padding and format detection

### Vector Search Optimization
- **Challenge**: Initial vector similarity searches returned irrelevant results
- **Solution**: Implemented threshold-based filtering and better document chunking

## Future Improvements

- Enhanced multilingual model fine-tuning
- User feedback incorporation for continuous learning
- Integration with ticketing systems
- Performance optimizations for larger knowledge bases
- Advanced analytics dashboard

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built as part of CSCI 5411: Advanced Cloud Architecting
- Inspired by real-world customer support challenges
- Leverages open-source embedding models

## Contribution
- If anyone want to contribute to this project, feel free to fork and contribute!