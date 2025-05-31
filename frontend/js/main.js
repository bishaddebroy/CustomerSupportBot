document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const fileUpload = document.getElementById('file-upload');
    const uploadModal = document.getElementById('upload-modal');
    const closeModal = document.querySelector('.close-modal');
    const selectFileBtn = document.getElementById('select-file-btn');
    const confirmUploadBtn = document.getElementById('confirm-upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    const uploadProgress = document.getElementById('upload-progress');
    
    // Generate a session ID for this chat session
    const sessionId = 'session_' + Math.random().toString(36).substring(2, 15);
    
    // API endpoints
    const API_URL = "https://bzswdbk000.execute-api.us-east-1.amazonaws.com/prod";
    const CHAT_ENDPOINT = `${API_URL}/api/chat`;
    const UPLOAD_ENDPOINT = `${API_URL}/api/upload`;
    
    // Initialize chat
    init();
    
    function init() {
        // Set up event listeners
        chatInput.addEventListener('keypress', handleInputKeypress);
        sendBtn.addEventListener('click', sendMessage);
        uploadBtn.addEventListener('click', openUploadModal);
        closeModal.addEventListener('click', closeUploadModal);
        selectFileBtn.addEventListener('click', () => fileUpload.click());
        fileUpload.addEventListener('change', handleFileSelect);
        confirmUploadBtn.addEventListener('click', uploadDocument);
        
        // Auto-resize textarea
        chatInput.addEventListener('input', autoResizeTextarea);
        
        // Check health status on load
        checkHealth();
    }
    
    function autoResizeTextarea() {
        chatInput.style.height = 'auto';
        chatInput.style.height = chatInput.scrollHeight + 'px';
    }
    
    function handleInputKeypress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }
    
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessageToChat('user', message);
        
        // Clear input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        
        // Add typing indicator
        const typingIndicator = addTypingIndicator();
        
        // Send message to API
        fetch(CHAT_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                session_id: sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Add bot response
            if (data.success) {
                addMessageToChat('bot', data.response);
            } else {
                addMessageToChat('bot', `Error: ${data.error || 'Unknown error occurred'}`);
            }
        })
        .catch(error => {
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Add error message
            addMessageToChat('bot', `I'm sorry, there was an error processing your request. Please try again later.`);
            console.error('Error sending message:', error);
        });
    }
    
    function addMessageToChat(sender, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Process message content
        let formattedContent = content;
        
        // If it's a bot message, check for citation markers
        if (sender === 'bot') {
            // Replace citation markers with styled spans
            formattedContent = formattedContent.replace(/\[Document (\d+)\]/g, 
                '<span class="source">Source $1</span>');
        }
        
        // Add paragraphs
        const paragraphs = formattedContent.split('\n').filter(p => p.trim() !== '');
        paragraphs.forEach(paragraph => {
            const p = document.createElement('p');
            p.innerHTML = paragraph;
            messageContent.appendChild(p);
        });
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot typing-indicator';
        
        const typingContent = document.createElement('div');
        typingContent.className = 'message-content';
        
        const dots = document.createElement('div');
        dots.className = 'typing-dots';
        dots.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        
        typingContent.appendChild(dots);
        typingDiv.appendChild(typingContent);
        chatMessages.appendChild(typingDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return typingDiv;
    }
    
    function openUploadModal() {
        uploadModal.style.display = 'flex';
        resetUploadState();
    }
    
    function closeUploadModal() {
        uploadModal.style.display = 'none';
    }
    
    function resetUploadState() {
        fileUpload.value = '';
        uploadStatus.textContent = '';
        uploadProgress.style.width = '0';
        confirmUploadBtn.disabled = true;
    }
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const validTypes = ['.pdf', '.txt', '.docx'];
        const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        
        if (!validTypes.includes(fileExtension)) {
            uploadStatus.textContent = 'Invalid file type. Please select a PDF, TXT, or DOCX file.';
            uploadStatus.className = 'text-error';
            return;
        }
        
        uploadStatus.textContent = `Selected file: ${file.name}`;
        uploadStatus.className = '';
        confirmUploadBtn.disabled = false;
    }
    
    // This function should be attached to your upload button or form submission
    function uploadDocument() {
        const file = fileUpload.files[0];
        if (!file) {
            uploadStatus.textContent = 'Please select a file first.';
            uploadStatus.className = 'text-error';
            return;
        }
        
        // Update UI
        uploadStatus.textContent = 'Uploading...';
        confirmUploadBtn.disabled = true;
        uploadProgress.style.width = '0';
        
        // Create a FileReader to convert the file to base64
        const reader = new FileReader();
        
        reader.onload = function(e) {
            // Get the base64 data from the FileReader result
            // The result looks like: "data:application/pdf;base64,JVBERi0xLjQKJ..." 
            // We need to extract just the base64 part after the comma
            const base64Data = e.target.result.split(',')[1];
            
            // Send the base64 data to the API
            fetch(UPLOAD_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file: base64Data,
                    filename: file.name
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    uploadStatus.textContent = data.message || 'Document uploaded successfully!';
                    uploadStatus.className = 'text-success';
                    uploadProgress.style.width = '100%';
                    
                    // Add system message to chat
                    addMessageToChat('bot', `I've learned new information from "${file.name}". You can now ask me questions about it!`);
                    
                    // Close modal after delay
                    setTimeout(closeUploadModal, 2000);
                } else {
                    uploadStatus.textContent = `Error: ${data.error || 'Unknown error'}`;
                    uploadStatus.className = 'text-error';
                    confirmUploadBtn.disabled = false;
                }
            })
            .catch(error => {
                uploadStatus.textContent = 'Upload failed. Please try again.';
                uploadStatus.className = 'text-error';
                confirmUploadBtn.disabled = false;
                console.error('Error uploading document:', error);
            });
        };
        
        reader.onerror = function() {
            uploadStatus.textContent = 'Error reading file. Please try again.';
            uploadStatus.className = 'text-error';
            confirmUploadBtn.disabled = false;
        };
        
        // Read the file as a Data URL (which includes base64 encoding)
        reader.readAsDataURL(file);
    }

    // If you're using a text input instead of file upload (for testing)
    function uploadTextDocument() {
        const textContent = document.getElementById('textInput').value;
        if (!textContent) {
            alert('Please enter some text');
            return;
        }
        
        // Convert text to base64
        const base64Data = btoa(textContent);
        
        fetch(UPLOAD_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file: base64Data,
                filename: 'text-input.txt'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Text uploaded successfully!');
            } else {
                alert(`Error: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            alert('Upload failed. Please try again.');
            console.error('Error uploading text:', error);
        });
    }
    
    function checkHealth() {
        fetch(`${API_URL}/api/health`)
            .then(response => response.json())
            .then(data => {
                console.log('Health status:', data);
                if (data.status !== 'healthy') {
                    // Show warning if service is not healthy
                    addMessageToChat('bot', 'Warning: Some services may not be functioning properly. Your experience might be affected.');
                }
            })
            .catch(error => {
                console.error('Error checking health:', error);
            });
    }
});