#!/usr/bin/env python3
"""
Integration test for Azure AI Foundry agent endpoint
"""

import pytest
import requests
import time
import subprocess
import os
import signal
from pathlib import Path

class TestAgentIntegration:
    """Test the /agents/test endpoint with real Azure AI Foundry integration"""
    
    @classmethod
    def setup_class(cls):
        """Start the FastAPI server for testing"""
        cls.server_process = None
        cls.base_url = "http://localhost:8003"
        
        # Start server in background
        project_root = Path(__file__).parent
        cmd = [
            "bash", "-c", 
            f"cd {project_root} && source venv/bin/activate && python src/backend/main_simple_foundry.py"
        ]
        
        cls.server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for server to start
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=2)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)
        else:
            pytest.fail("Server failed to start within 10 seconds")
    
    @classmethod
    def teardown_class(cls):
        """Stop the FastAPI server"""
        if cls.server_process:
            # Kill the process group to ensure cleanup
            os.killpg(os.getpgid(cls.server_process.pid), signal.SIGTERM)
            cls.server_process.wait(timeout=5)
    
    def test_health_endpoint(self):
        """Test that the health endpoint responds"""
        response = requests.get(f"{self.base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_agent_list_endpoint(self):
        """Test that we can list agents"""
        response = requests.get(f"{self.base_url}/agents/list")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) > 0
        # Should have at least the Agile Coaching Agent
        agent_names = [agent["name"] for agent in data["agents"]]
        assert any("AgileCoachingAgent" in name for name in agent_names)
    
    def test_agent_interaction_success(self):
        """Test successful agent interaction"""
        payload = {
            "message": "Can you help me with sprint planning?"
        }
        
        response = requests.post(
            f"{self.base_url}/agents/test",
            json=payload,
            timeout=45  # Allow time for agent response
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["success"] is True
        assert "agent_name" in data
        assert "agent_id" in data
        assert "thread_id" in data
        assert "run_id" in data
        assert data["run_status"] == "completed"
        assert "response" in data
        assert "timestamp" in data
        
        # Verify response content
        assert len(data["response"]) > 50  # Should be a substantial response
        assert "sprint" in data["response"].lower()  # Should mention sprint planning
        assert data["agent_name"] == "SM-Asst-AgileCoachingAgent"
        
        # Verify IDs are properly formatted
        assert data["thread_id"].startswith("thread_")
        assert data["run_id"].startswith("run_")
        assert data["agent_id"].startswith("asst_")
    
    def test_agent_interaction_empty_message(self):
        """Test agent interaction with empty message"""
        payload = {"message": ""}
        
        response = requests.post(
            f"{self.base_url}/agents/test",
            json=payload,
            timeout=30
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_agent_interaction_missing_message(self):
        """Test agent interaction with missing message field"""
        payload = {}
        
        response = requests.post(
            f"{self.base_url}/agents/test",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 422  # FastAPI validation error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])