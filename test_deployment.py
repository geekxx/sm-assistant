#!/usr/bin/env python3
"""
Test script for the simplified SM Assistant API
"""

import asyncio
import aiohttp
import json

async def test_api(base_url="https://sm-assistant-production.up.railway.app"):
    """Test the SM Assistant API endpoints"""
    
    print(f"🧪 Testing SM Assistant API at {base_url}")
    
    async with aiohttp.ClientSession() as session:
        
        # Test health endpoint
        print("\n1️⃣ Testing health check...")
        try:
            async with session.get(f"{base_url}/api/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                else:
                    print(f"❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test config endpoint
        print("\n2️⃣ Testing configuration...")
        try:
            async with session.get(f"{base_url}/api/config") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Config loaded: {len(data.get('agents', {}))} agents available")
                    print(f"   OpenAI available: {data.get('openai_available', False)}")
                else:
                    print(f"❌ Config failed: {response.status}")
        except Exception as e:
            print(f"❌ Config error: {e}")
        
        # Test agents endpoint
        print("\n3️⃣ Testing agents list...")
        try:
            async with session.get(f"{base_url}/api/agents") as response:
                if response.status == 200:
                    data = await response.json()
                    agents = data.get('agents', [])
                    print(f"✅ Agents loaded: {len(agents)} available")
                    for agent in agents[:3]:  # Show first 3
                        print(f"   - {agent['name']}: {agent['description']}")
                else:
                    print(f"❌ Agents failed: {response.status}")
        except Exception as e:
            print(f"❌ Agents error: {e}")
        
        # Test chat endpoint
        print("\n4️⃣ Testing chat functionality...")
        try:
            chat_data = {
                "message": "Hello! Can you help me create a user story for a login feature?",
                "agent_type": "backlog"
            }
            
            async with session.post(
                f"{base_url}/api/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Chat successful!")
                    print(f"   Agent: {data.get('agent', 'Unknown')}")
                    print(f"   Response: {data.get('response', 'No response')[:100]}...")
                else:
                    print(f"❌ Chat failed: {response.status}")
                    text = await response.text()
                    print(f"   Error: {text[:200]}...")
        except Exception as e:
            print(f"❌ Chat error: {e}")
        
        # Test frontend
        print("\n5️⃣ Testing frontend...")
        try:
            async with session.get(base_url) as response:
                if response.status == 200:
                    print(f"✅ Frontend accessible at {base_url}")
                else:
                    print(f"❌ Frontend failed: {response.status}")
        except Exception as e:
            print(f"❌ Frontend error: {e}")
    
    print(f"\n🎉 Testing complete! Your SM Assistant should be ready for demos at {base_url}")

if __name__ == "__main__":
    asyncio.run(test_api())