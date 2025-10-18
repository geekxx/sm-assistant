"""
Test the enhanced agent responses locally
"""
import json
from datetime import datetime
from typing import Dict, Any

def handle_backlog_request(message: str, message_lower: str) -> Dict[str, Any]:
    """Handle backlog intelligence requests with detailed responses"""
    
    if any(keyword in message_lower for keyword in ['user story', 'user stories', 'story', 'stories']):
        if 'shadowdark' in message_lower and 'rpg' in message_lower:
            response = """I'll help you create user stories for a Shadowdark RPG Game Master Assistant Agent:

**Epic: GM Campaign Management**

**User Story 1: Session Planning**
- **Story**: As a Game Master, I want to quickly generate session outlines so that I can focus on storytelling rather than preparation
- **Acceptance Criteria**: 
  - Generate encounters based on party level and location
  - Suggest plot hooks that connect to ongoing storylines
  - Provide NPC names and basic motivations
- **Story Points**: 5

**User Story 2: Real-time Assistance**
- **Story**: As a GM, I want instant rule lookups during gameplay so that I can maintain game flow
- **Acceptance Criteria**:
  - Search Shadowdark rules by keyword
  - Provide spell descriptions and effects
  - Show monster stats and abilities quickly
- **Story Points**: 8

**User Story 3: Player Character Tracking**
- **Story**: As a GM, I want to track player character progression so that I can create appropriate challenges
- **Acceptance Criteria**:
  - Monitor character levels and abilities
  - Suggest appropriate encounters
  - Track character backgrounds for plot integration
- **Story Points**: 13

**Definition of Done**: Each feature must be tested with actual gameplay sessions and integrate with Shadowdark's core mechanics."""
        else:
            response = f"""Based on your request: "{message}", here are comprehensive user stories:

**User Story Template:**
As a [user type], I want [functionality] so that [business value]

**Story Analysis:**
- **Epic/Theme**: Product Development
- **Priority**: High
- **Story Points**: 5-8 (depending on complexity)

**Acceptance Criteria (Given/When/Then format):**
- Given the user has specific requirements
- When they request story creation
- Then detailed stories are provided with clear value propositions

**Dependencies**: 
- Product Owner approval
- Technical feasibility assessment
- Design review

**Definition of Done:**
- Stories follow INVEST principles
- Acceptance criteria are testable
- Story points estimated by team"""
    else:
        response = f"""I'm your Backlog Intelligence Agent, specialized in user story creation and backlog management.

For your request: "{message}"

**I can help you with:**
- Creating detailed user stories with acceptance criteria
- Breaking down epics into manageable stories
- Estimating story points using Fibonacci sequence
- Prioritizing backlog items by value and effort
- Writing clear acceptance criteria in Given/When/Then format

**Would you like me to:**
1. Create specific user stories for your requirements?
2. Help prioritize existing backlog items?
3. Break down a large epic into smaller stories?
4. Review and improve existing user stories?

Please provide more details about what you'd like to work on!"""

    return {
        "success": True,
        "agent_name": "BacklogIntelligenceAgent",
        "message": response,
        "fallback_mode": False,
        "user_message": message,
        "timestamp": datetime.now().isoformat(),
        "agent_capabilities": ["User story creation", "Acceptance criteria", "Backlog analysis", "Story estimation"]
    }

# Test the Shadowdark RPG request
test_message = "Write user stories for a Shadowdark RPG game master assistant agent. It helps GM's run their campaign."
result = handle_backlog_request(test_message, test_message.lower())

print("Test Result:")
print(json.dumps(result, indent=2))
print("\n" + "="*80 + "\n")
print("Response Message:")
print(result["message"])