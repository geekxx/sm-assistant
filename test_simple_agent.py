#!/usr/bin/env python3
"""
Simple integration test for Azure AI Foundry agent endpoint
"""

import requests
import time

def test_agent_endpoint():
    """Test the /agents/test endpoint directly"""
    base_url = "http://localhost:8003"
    
    # Test health first
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        assert health_response.status_code == 200
        print("✅ Health check passed")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test agent interaction
    try:
        payload = {"message": "Can you help me with agile coaching?"}
        response = requests.post(
            f"{base_url}/agents/test",
            json=payload,
            timeout=45
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["success"] is True
        assert "agent_name" in data
        assert "response" in data
        assert len(data["response"]) > 50
        
        print("✅ Agent interaction test passed")
        print(f"   Agent: {data['agent_name']}")
        print(f"   Response length: {len(data['response'])} characters")
        print(f"   Run status: {data['run_status']}")
        return True
        
    except Exception as e:
        print(f"❌ Agent interaction test failed: {e}")
        return False

if __name__ == "__main__":
    test_agent_endpoint()