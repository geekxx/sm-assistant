#!/usr/bin/env python3
"""
Simple test server to check if the UI elements work without Azure dependencies
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/health")
async def health_check():
    """Simple health check without Azure dependency"""
    return {
        "status": "healthy",
        "azure_ai_foundry": "mock_connected",
        "agents_accessible": True,
        "agents_found": ["SM-Asst-BacklogIntelligence", "SM-Asst-MeetingIntelligence"],
        "total_agents": 2,
        "timestamp": "2025-10-17T10:00:00"
    }

@app.get("/agents/list")
async def list_agents():
    """Mock agents list"""
    return {
        "agents": [
            {"name": "SM-Asst-BacklogIntelligence", "id": "1", "status": "active"},
            {"name": "SM-Asst-MeetingIntelligence", "id": "2", "status": "active"}
        ]
    }

@app.post("/agents/chat")
async def chat_endpoint(request: dict):
    """Mock chat endpoint"""
    message = request.get("message", "")
    return {
        "success": True,
        "response": f"Mock response to: {message}",
        "agent_name": "SM-Asst-BacklogIntelligence",
        "run_status": "completed"
    }

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Demo page with chat interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SM-Assistant Demo - UI Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .chat-container { border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 10px; margin: 10px 0; }
            .chat-message { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .chat-message.user { background: #e3f2fd; }
            .chat-message.assistant { background: #f1f8e9; }
            .chat-message.system { background: #fff3e0; }
            .chat-input-container { display: flex; gap: 10px; margin: 10px 0; }
            textarea { flex: 1; padding: 10px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .example-prompt { background: #f8f9fa; padding: 5px 10px; margin: 5px; border-radius: 3px; cursor: pointer; display: inline-block; }
            .example-prompt:hover { background: #e9ecef; }
        </style>
    </head>
    <body>
        <h1>🤖 SM-Assistant Demo - UI Test</h1>
        
        <div class="section">
            <h3>💬 General Chat Interface</h3>
            <div class="examples">
                <span class="example-prompt" onclick="setChatMessage(this.textContent)">Create user stories for a new checkout feature</span>
                <span class="example-prompt" onclick="setChatMessage(this.textContent)">Analyze our team's velocity trends</span>
                <span class="example-prompt" onclick="setChatMessage(this.textContent)">Help improve our retrospective meetings</span>
            </div>
            <div class="chat-container" id="chat-container">
                <!-- Chat messages will appear here -->
            </div>
            <div class="chat-input-container">
                <textarea id="chat-input" placeholder="Ask the SM-Assistant anything..." rows="3"></textarea>
                <button onclick="sendChatMessage()" id="chat-send-btn">Send</button>
            </div>
            <div style="margin-top: 10px;">
                <button onclick="clearChat()" style="background: #6c757d;">Clear Chat</button>
                <button onclick="testBasicFunctionality()" style="background: #28a745;">Test UI</button>
            </div>
        </div>

        <script>
            console.log('Demo page loaded');
            
            function setChatMessage(message) {
                console.log('setChatMessage called with:', message);
                const input = document.getElementById('chat-input');
                console.log('Input element found:', input);
                if (input) {
                    input.value = message;
                    console.log('Message set to input');
                } else {
                    console.error('Input element not found!');
                }
            }
            
            function addChatMessage(type, content) {
                console.log('addChatMessage called:', type, content);
                const chatContainer = document.getElementById('chat-container');
                console.log('Chat container found:', chatContainer);
                
                if (!chatContainer) {
                    console.error('Chat container not found!');
                    return;
                }
                
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${type}`;
                
                const timestamp = new Date().toLocaleTimeString();
                const typeIcon = type === 'user' ? '👤' : type === 'assistant' ? '🤖' : '💡';
                
                messageDiv.innerHTML = `
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">
                        ${typeIcon} ${type.charAt(0).toUpperCase() + type.slice(1)} - ${timestamp}
                    </div>
                    <div>${content}</div>
                `;
                
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                console.log('Message added to chat');
            }
            
            async function sendChatMessage() {
                console.log('sendChatMessage called');
                const input = document.getElementById('chat-input');
                const message = input.value.trim();
                
                console.log('Message:', message);
                
                if (!message) {
                    alert('Please enter a message');
                    return;
                }
                
                // Add user message
                addChatMessage('user', message);
                input.value = '';
                
                // Add thinking message
                addChatMessage('system', '🤔 Processing your request...');
                
                try {
                    const response = await fetch('/agents/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message })
                    });
                    
                    const data = await response.json();
                    console.log('Response:', data);
                    
                    if (data.success) {
                        addChatMessage('assistant', data.response);
                        addChatMessage('system', `✅ Response from ${data.agent_name}`);
                    } else {
                        addChatMessage('system', `❌ Error: ${data.error || 'Unknown error'}`);
                    }
                } catch (error) {
                    console.error('Chat error:', error);
                    addChatMessage('system', `❌ Error: ${error.message}`);
                }
            }
            
            function clearChat() {
                console.log('clearChat called');
                const chatContainer = document.getElementById('chat-container');
                if (chatContainer) {
                    chatContainer.innerHTML = '';
                    console.log('Chat cleared');
                } else {
                    console.error('Chat container not found!');
                }
            }
            
            function testBasicFunctionality() {
                console.log('Testing basic functionality...');
                addChatMessage('system', 'Testing UI functionality...');
                addChatMessage('user', 'This is a test user message');
                addChatMessage('assistant', 'This is a test assistant response');
                addChatMessage('system', '✅ UI test completed successfully!');
            }
            
            // Add Enter key support
            document.getElementById('chat-input').addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
            
            // Test on load
            window.onload = function() {
                console.log('Window loaded');
                addChatMessage('system', '🚀 SM-Assistant UI Test Page Loaded! Click example prompts or type a message.');
            };
        </script>
    </body>
    </html>
    '''

if __name__ == "__main__":
    print("Starting simple UI test server...")
    uvicorn.run(app, host="0.0.0.0", port=8004)