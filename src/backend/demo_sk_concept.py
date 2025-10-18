"""
Demo: Semantic Kernel + Azure AI Foundry Integration 
Shows the concept of intelligent multi-agent orchestration
"""

import asyncio
import logging
from datetime import datetime
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockSKAgent:
    """Mock SK Agent to demonstrate the concept"""
    def __init__(self, name: str, capability: str, description: str):
        self.name = name
        self.capability = capability
        self.description = description
    
    async def invoke(self, message: str) -> str:
        """Simulate agent processing"""
        await asyncio.sleep(0.5)  # Simulate processing time
        return f"[{self.name}] {self.capability} response to: '{message}'"

class MockOrchestration:
    """Mock orchestration to demonstrate multi-agent selection"""
    def __init__(self, agents: List[MockSKAgent]):
        self.agents = agents
    
    def analyze_intent(self, message: str) -> str:
        """Analyze message and select best agent"""
        message_lower = message.lower()
        
        # Simple routing logic (enhanced version is in main_intelligent_orchestration.py)
        if any(word in message_lower for word in ["story", "backlog", "requirement"]):
            return "BacklogIntelligence"
        elif any(word in message_lower for word in ["meeting", "standup", "retrospective"]):
            return "MeetingIntelligence"
        elif any(word in message_lower for word in ["metrics", "velocity", "performance"]):
            return "FlowMetrics"
        elif any(word in message_lower for word in ["wellness", "burnout", "morale"]):
            return "TeamWellness"
        else:
            return "AgileCoaching"  # Default
    
    async def orchestrate(self, message: str) -> str:
        """Demonstrate multi-agent orchestration"""
        logger.info(f"🎯 Orchestrating: {message}")
        
        # Step 1: Intelligent agent selection
        selected_capability = self.analyze_intent(message)
        selected_agent = next((a for a in self.agents if a.capability == selected_capability), self.agents[0])
        
        logger.info(f"🤖 Selected agent: {selected_agent.name} ({selected_capability})")
        
        # Step 2: Agent invocation
        response = await selected_agent.invoke(message)
        
        # Step 3: Multi-agent collaboration (if needed)
        if "help" in message.lower() or "complex" in message.lower():
            logger.info("🔄 Engaging additional agents for collaboration...")
            
            # Get insights from other relevant agents
            additional_responses = []
            for agent in self.agents[:2]:  # Get 2 additional agents
                if agent != selected_agent:
                    additional_response = await agent.invoke(f"Provide supporting insights for: {message}")
                    additional_responses.append(additional_response)
            
            # Combine responses
            if additional_responses:
                response += "\n\n🤝 Additional insights:\n" + "\n".join(additional_responses)
        
        return response


async def demo_sk_orchestration():
    """Demonstrate Semantic Kernel orchestration concept"""
    print("🚀 SM-Assistant Semantic Kernel + Azure AI Foundry Integration Demo")
    print("=" * 70)
    
    # Create mock agents representing our SM-Assistant capabilities
    agents = [
        MockSKAgent("SM-Asst-BacklogIntelligenceAgent", "BacklogIntelligence", 
                   "User story creation and backlog analysis"),
        MockSKAgent("SM-Asst-MeetingIntelligenceAgent", "MeetingIntelligence", 
                   "Meeting analysis and action item extraction"),
        MockSKAgent("SM-Asst-FlowMetricsAgent", "FlowMetrics", 
                   "Delivery metrics and bottleneck analysis"),
        MockSKAgent("SM-Asst-TeamWellnessAgent", "TeamWellness", 
                   "Team sentiment and wellness monitoring"),
        MockSKAgent("SM-Asst-AgileCoachingAgent", "AgileCoaching", 
                   "Strategic agile coaching and guidance"),
    ]
    
    # Create orchestration system
    orchestration = MockOrchestration(agents)
    
    # Test scenarios demonstrating intelligent routing
    test_scenarios = [
        "Create user stories for a new login feature",
        "Analyze the team's daily standup meeting transcript", 
        "Show me the team's velocity metrics for this sprint",
        "The team seems stressed - check their wellness indicators",
        "Help improve our agile process with complex recommendations"
    ]
    
    print(f"📋 Available agents: {[agent.name for agent in agents]}")
    print()
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"🧪 Scenario {i}: {scenario}")
        print("-" * 50)
        
        start_time = datetime.now()
        result = await orchestration.orchestrate(scenario)
        end_time = datetime.now()
        
        print(f"📝 Result:\n{result}")
        print(f"⏱️  Processing time: {(end_time - start_time).total_seconds():.2f}s")
        print()
    
    print("🎉 Demo complete! This shows the concept of:")
    print("   ✅ Intelligent agent selection based on message analysis")
    print("   ✅ Multi-agent collaboration for complex scenarios")
    print("   ✅ Semantic Kernel orchestration patterns")
    print("   ✅ Azure AI Foundry agent integration potential")
    print()
    print("🔗 Next steps:")
    print("   • Replace mock agents with real Azure AI Foundry agents")
    print("   • Integrate with actual OrchestrationManager")
    print("   • Add human-in-the-loop workflows via ProxyAgent")
    print("   • Enable MCP tool integration for external systems")


if __name__ == "__main__":
    asyncio.run(demo_sk_orchestration())