"""
Alternative authentication approach using API keys instead of managed identity.
This bypasses the DefaultAzureCredential issue in Railway.
"""

import os
import logging
from typing import Optional

# Simple API key based Azure AI client
class SimpleAzureAIClient:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
    
    async def test_connection(self) -> bool:
        """Test if we can connect to Azure AI"""
        try:
            import aiohttp
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.endpoint}/openai/deployments", headers=headers) as response:
                    if response.status == 200:
                        self.logger.info(f"✅ Azure AI connected via API key: {self.endpoint}")
                        return True
                    else:
                        self.logger.error(f"❌ Azure AI connection failed: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ Azure AI connection error: {e}")
            return False

def get_simple_azure_client() -> Optional[SimpleAzureAIClient]:
    """Get a simple Azure AI client using API key authentication"""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    if endpoint and api_key:
        return SimpleAzureAIClient(endpoint, api_key)
    return None