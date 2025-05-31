import re
import logging
import io
from typing import List, Dict, Any
import base64

# Initialize logger
logger = logging.getLogger()

def extract_text(file_content: bytes, file_extension: str) -> str:
    """
    Extract text from various file formats
    
    Args:
        file_content: Binary content of the file
        file_extension: File extension (e.g., '.pdf', '.txt', '.docx')
        
    Returns:
        Extracted text as string
    """
    try:
        # Handle different file types
        if file_extension == '.txt':
            # For text files, try different encodings
            return decode_with_fallback(file_content)
            
        elif file_extension == '.pdf':
            # For PDF files
            return extract_text_from_pdf(file_content)
            
        elif file_extension in ['.docx', '.doc']:
            # For Word documents
            return extract_text_from_docx(file_content)
            
        else:
            logger.error(f"Unsupported file type: {file_extension}")
            return ""
            
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}", exc_info=True)
        return ""

def decode_with_fallback(content: bytes) -> str:
    """
    Try to decode bytes with different encodings
    
    Args:
        content: Bytes to decode
        
    Returns:
        Decoded string
    """
    # Try encodings in order of likelihood
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            # Try to decode with the current encoding
            decoded = content.decode(encoding)
            
            # Check if the result contains only valid characters
            # Replace any remaining problematic characters with space
            cleaned = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in decoded)
            
            return cleaned
        except UnicodeDecodeError:
            # Try the next encoding
            continue
    
    # If all encodings fail, use replace error handler with utf-8
    return content.decode('utf-8', errors='replace')

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF file
    
    Args:
        file_content: Binary content of the PDF file
        
    Returns:
        Extracted text
    """
    try:
        # Import here to reduce cold start time when not needed
        import PyPDF2
        from io import BytesIO
        
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            
            # Clean any non-printable characters
            page_text = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in page_text)
            text += page_text + "\n"
            
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}", exc_info=True)
        return ""

def extract_text_from_docx(file_content: bytes) -> str:
    """
    Extract text from DOCX file
    
    Args:
        file_content: Binary content of the DOCX file
        
    Returns:
        Extracted text
    """
    try:
        # Import here to reduce cold start time when not needed
        import docx
        from io import BytesIO
        
        doc_file = BytesIO(file_content)
        doc = docx.Document(doc_file)
        
        text = ""
        for para in doc.paragraphs:
            para_text = para.text
            
            # Clean any non-printable characters
            para_text = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in para_text)
            text += para_text + "\n"
            
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}", exc_info=True)
        return ""

def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for processing
    
    Args:
        text: Input text to split
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Clean the text to ensure all characters are valid
    # Replace any problematic characters with spaces
    text = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # If text is shorter than chunk_size, return it as a single chunk
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        # Find the end of the chunk
        end = start + chunk_size
        
        if end >= len(text):
            # Last chunk
            chunks.append(text[start:])
            break
        
        # Try to find a natural break point (end of sentence)
        # Look for '.', '!', or '?' followed by a space or newline
        natural_break = -1
        for i in range(end - 1, max(start, end - 200), -1):
            if i < len(text) and text[i] in ['.', '!', '?'] and (i+1 >= len(text) or text[i+1].isspace()):
                natural_break = i + 1
                break
        
        if natural_break != -1:
            chunks.append(text[start:natural_break])
            start = natural_break - overlap
        else:
            # If no natural break found, just use the chunk size
            chunks.append(text[start:end])
            start = end - overlap
    
    return chunks