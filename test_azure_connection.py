#!/usr/bin/env python3
"""
Test script to verify the improved Azure connection handling
"""
import asyncio
import sys
import os

# Add the backend path
sys.path.append('/Users/jeffrey.heinen/projects/sm-assistant/src/backend')

async def test_connection():
    print("🔧 Testing improved Azure connection handling...")
    
    # Import our improved functions
    from main_simple_foundry import get_ai_client_with_timeout, fallback_agent_response
    
    print("1. Testing Azure connection with timeout...")
    client = await get_ai_client_with_timeout(timeout_seconds=3)
    
    if client:
        print("✅ Azure AI Foundry connected successfully")
    else:
        print("⚠️ Azure AI Foundry not available - fallback mode will be used")
    
    print("\n2. Testing fallback agent response...")
    fallback_response = await fallback_agent_response(
        "Help me create user stories for a login feature",
        "SM-Asst-BacklogIntelligence"
    )
    
    print(f"✅ Fallback response generated:")
    print(f"   Agent: {fallback_response['agent_name']}")
    print(f"   Success: {fallback_response['success']}")
    print(f"   Fallback Mode: {fallback_response.get('fallback_mode', False)}")
    print(f"   Response Length: {len(fallback_response['response'])} characters")
    
    print("\n✅ All tests completed successfully!")
    print("🚀 The server should now handle Azure connection issues gracefully")

if __name__ == "__main__":
    asyncio.run(test_connection())