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
    
    # Test agent listing (should show only SM-Asst agents)
    try:
        list_response = requests.get(f"{base_url}/agents/list", timeout=10)
        assert list_response.status_code == 200
        data = list_response.json()
        assert "sm_asst_count" in data
        assert data["sm_asst_count"] > 0
        print(f"✅ Agent listing passed - Found {data['sm_asst_count']} SM-Asst agents out of {data['total_count']} total")
    except Exception as e:
        print(f"❌ Agent listing failed: {e}")
        return False
    
    # Test general agent interaction (first available SM-Asst agent)
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
        assert data["agent_name"].startswith("SM-Asst-")
        assert "response" in data
        assert len(data["response"]) > 50
        
        print("✅ General agent interaction test passed")
        print(f"   Agent: {data['agent_name']}")
        print(f"   Response length: {len(data['response'])} characters")
        return True
        
    except Exception as e:
        print(f"❌ Agent interaction test failed: {e}")
        return False
    
    # Test specific agent routing
    try:
        payload = {
            "message": "Help me analyze my backlog for upcoming sprint", 
            "agent_name": "SM-Asst-BacklogIntelligenceAgent"
        }
        response = requests.post(
            f"{base_url}/agents/test",
            json=payload,
            timeout=45
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["agent_name"] == "SM-Asst-BacklogIntelligenceAgent"
        
        print("✅ Specific agent routing test passed")
        print(f"   Selected agent: {data['agent_name']}")
        return True
        
    except Exception as e:
        print(f"❌ Specific agent routing test failed: {e}")
        return False

if __name__ == "__main__":
    test_agent_endpoint()