"""
Backlog Intelligence Agent for Scrum Master Assistant
Specializes in user story creation, acceptance criteria, and backlog analysis.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
from semantic_kernel.functions import KernelFunctionFromPrompt

logger = logging.getLogger(__name__)

class BacklogIntelligenceAgent:
    """Agent specialized in backlog management and user story creation"""
    
    def __init__(self, kernel: Kernel, deployment_name: str):
        self.kernel = kernel
        self.deployment_name = deployment_name
        self.agent_name = "BacklogIntelligenceAgent"
        
        # Initialize prompts for different capabilities
        self._init_prompts()
    
    def _init_prompts(self):
        """Initialize prompt templates for various backlog operations"""
        
        # User story creation prompt
        self.story_creation_prompt = """
You are an expert Product Owner and Business Analyst. Create comprehensive user stories from the given requirements.

Requirements: {{$requirements}}
Context: {{$context}}

For each user story, provide:
1. **User Story**: As a [persona], I want [functionality] so that [value/benefit]
2. **Acceptance Criteria**: Clear, testable criteria in Given/When/Then format
3. **Story Points**: Estimation with reasoning (Fibonacci: 1, 2, 3, 5, 8, 13, 21)
4. **Dependencies**: Technical or business dependencies
5. **Definition of Done**: Specific completion criteria
6. **Epic/Theme**: Connection to larger business goals

Guidelines:
- Focus on user value and outcomes
- Make stories independent, negotiable, valuable, estimable, small, and testable (INVEST)
- Include edge cases and error scenarios in acceptance criteria
- Consider accessibility, performance, and security where relevant
- Suggest story splitting if stories are too large

Format as JSON array with this structure:
```json
[
  {
    "title": "Clear, concise title",
    "user_story": "As a... I want... so that...",
    "acceptance_criteria": [
      "Given... When... Then...",
      "Given... When... Then..."
    ],
    "story_points": 5,
    "estimation_reasoning": "Why this estimation...",
    "dependencies": ["Dependency 1", "Dependency 2"],
    "definition_of_done": ["Criteria 1", "Criteria 2"],
    "epic": "Epic name or theme",
    "labels": ["label1", "label2"],
    "priority": "High/Medium/Low",
    "technical_notes": "Any technical considerations"
  }
]
```
"""

        # Backlog analysis prompt
        self.backlog_analysis_prompt = """
You are an experienced Scrum Master analyzing a product backlog for sprint readiness.

Backlog Items: {{$backlog_items}}
Sprint Capacity: {{$sprint_capacity}}
Team Velocity: {{$team_velocity}}

Analyze the backlog and provide:

1. **Readiness Assessment**: Which stories are ready for sprint planning?
2. **Gap Analysis**: What's missing from each story?
3. **Priority Recommendations**: Suggested prioritization based on value, risk, dependencies
4. **Capacity Planning**: Recommended stories for next sprint
5. **Risk Assessment**: Technical, business, or dependency risks
6. **Refinement Needs**: Stories needing further refinement

For each story, evaluate:
- Clarity of acceptance criteria
- Appropriate size (not too large)
- Clear definition of done
- Dependencies resolved or manageable
- Business value understood
- Technical approach feasible

Format as JSON:
```json
{
  "summary": {
    "total_stories": 0,
    "ready_stories": 0,
    "needs_refinement": 0,
    "blocked_stories": 0,
    "estimated_capacity_needed": 0
  },
  "ready_for_sprint": [
    {
      "story_key": "PROJ-123",
      "title": "Story title",
      "story_points": 5,
      "readiness_score": 9,
      "reasoning": "Why it's ready..."
    }
  ],
  "needs_refinement": [
    {
      "story_key": "PROJ-124", 
      "title": "Story title",
      "issues": ["Missing acceptance criteria", "Too large"],
      "recommendations": ["Split into smaller stories", "Add AC"]
    }
  ],
  "sprint_recommendations": {
    "suggested_stories": ["PROJ-123", "PROJ-125"],
    "total_points": 21,
    "capacity_utilization": "85%",
    "risk_factors": ["New technology in PROJ-126"]
  },
  "overall_recommendations": [
    "Focus refinement on stories X, Y, Z",
    "Consider breaking down epic ABC",
    "Address dependency on external team"
  ]
}
```
"""

        # Acceptance criteria generation prompt  
        self.acceptance_criteria_prompt = """
You are a Quality Assurance expert creating comprehensive acceptance criteria.

User Story: {{$user_story}}
Context: {{$context}}
Additional Requirements: {{$additional_requirements}}

Create detailed acceptance criteria that cover:

1. **Happy Path Scenarios**: Normal user flows
2. **Edge Cases**: Boundary conditions, unusual inputs
3. **Error Scenarios**: What happens when things go wrong
4. **Non-functional Requirements**: Performance, security, accessibility
5. **Integration Points**: How it works with other systems
6. **Data Validation**: Input validation and constraints

Use Given/When/Then format:
- **Given**: Initial state/context
- **When**: Action performed
- **Then**: Expected outcome

Include:
- Specific test data examples
- Expected error messages
- Performance criteria where relevant
- Accessibility requirements
- Security considerations

Format as JSON:
```json
{
  "user_story": "As a... I want... so that...",
  "acceptance_criteria": [
    {
      "scenario": "Happy path - successful action",
      "given": "User is logged in and has permissions",
      "when": "User performs valid action X",
      "then": "System responds with expected result Y"
    },
    {
      "scenario": "Error handling - invalid input", 
      "given": "User provides invalid data",
      "when": "User submits the form",
      "then": "System shows clear error message and preserves valid data"
    }
  ],
  "definition_of_done": [
    "All acceptance criteria pass",
    "Code reviewed and approved",
    "Unit tests written and passing",
    "Integration tests passing",
    "Accessibility guidelines met",
    "Security review completed",
    "Documentation updated"
  ],
  "test_data_examples": {
    "valid_inputs": ["example1", "example2"],
    "invalid_inputs": ["bad_example1", "bad_example2"],
    "edge_cases": ["boundary_case1", "boundary_case2"]
  }
}
```
"""

        # Epic breakdown prompt
        self.epic_breakdown_prompt = """
You are a Product Owner breaking down an epic into manageable user stories.

Epic Description: {{$epic_description}}
Target Users: {{$target_users}}
Business Goals: {{$business_goals}}
Technical Constraints: {{$technical_constraints}}

Break down the epic into user stories that:
1. Deliver incremental value
2. Can be completed in 1-2 sprints each
3. Follow logical dependency order
4. Enable early feedback and validation

For each story:
- Clear user value proposition
- Minimal viable implementation
- Testable outcomes
- Reasonable estimation (1-13 story points)

Consider:
- Walking skeleton approach (end-to-end thin slice)
- Risk reduction (tackle unknowns early)
- User feedback opportunities
- Technical learning and validation

Format as JSON:
```json
{
  "epic": {
    "name": "Epic name",
    "description": "Epic description",
    "business_value": "Why this epic matters",
    "success_criteria": ["Measurable outcome 1", "Outcome 2"]
  },
  "stories": [
    {
      "sequence": 1,
      "title": "Walking skeleton - basic flow",
      "user_story": "As a... I want... so that...",
      "story_points": 8,
      "rationale": "Why this story comes first",
      "value": "What value it delivers",
      "dependencies": [],
      "acceptance_criteria": ["AC1", "AC2"],
      "risks": ["Risk if any"]
    }
  ],
  "implementation_strategy": {
    "approach": "Incremental delivery strategy",
    "milestones": ["Milestone 1", "Milestone 2"],
    "feedback_points": ["When to gather user feedback"],
    "technical_risks": ["Key technical challenges"]
  }
}
```
"""

    async def create_user_stories(self, requirements: str, context: str = "") -> Dict[str, Any]:
        """Create user stories from raw requirements"""
        try:
            function = KernelFunctionFromPrompt(
                function_name="create_user_stories",
                prompt=self.story_creation_prompt,
                prompt_template_config=PromptTemplateConfig(
                    input_variables=[
                        InputVariable(name="requirements"),
                        InputVariable(name="context")
                    ]
                )
            )
            
            result = await self.kernel.invoke(
                function,
                requirements=requirements,
                context=context or "No additional context provided"
            )
            
            # Parse the JSON response
            response_text = str(result)
            
            # Clean up the response to extract JSON
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                stories_json = json.loads(json_match.group())
                return {
                    "success": True,
                    "stories": stories_json,
                    "count": len(stories_json)
                }
            else:
                return {
                    "success": False,
                    "error": "Could not parse user stories from response",
                    "raw_response": response_text
                }
                
        except Exception as e:
            logger.error(f"Error creating user stories: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_backlog(self, backlog_items: List[Dict], 
                            sprint_capacity: int = 21, 
                            team_velocity: int = 18) -> Dict[str, Any]:
        """Analyze backlog readiness for sprint planning"""
        try:
            # Format backlog items for analysis
            backlog_text = json.dumps(backlog_items, indent=2)
            
            function = KernelFunctionFromPrompt(
                function_name="analyze_backlog",
                prompt=self.backlog_analysis_prompt,
                prompt_template_config=PromptTemplateConfig(
                    input_variables=[
                        InputVariable(name="backlog_items"),
                        InputVariable(name="sprint_capacity"),
                        InputVariable(name="team_velocity")
                    ]
                )
            )
            
            result = await self.kernel.invoke(
                function,
                backlog_items=backlog_text,
                sprint_capacity=str(sprint_capacity),
                team_velocity=str(team_velocity)
            )
            
            response_text = str(result)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    "success": True,
                    "analysis": analysis,
                    "analyzed_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Could not parse backlog analysis",
                    "raw_response": response_text
                }
                
        except Exception as e:
            logger.error(f"Error analyzing backlog: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_acceptance_criteria(self, user_story: str, 
                                         context: str = "",
                                         additional_requirements: str = "") -> Dict[str, Any]:
        """Generate comprehensive acceptance criteria for a user story"""
        try:
            function = KernelFunctionFromPrompt(
                function_name="generate_acceptance_criteria",
                prompt=self.acceptance_criteria_prompt,
                prompt_template_config=PromptTemplateConfig(
                    input_variables=[
                        InputVariable(name="user_story"),
                        InputVariable(name="context"),
                        InputVariable(name="additional_requirements")
                    ]
                )
            )
            
            result = await self.kernel.invoke(
                function,
                user_story=user_story,
                context=context or "No additional context",
                additional_requirements=additional_requirements or "No additional requirements"
            )
            
            response_text = str(result)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                criteria = json.loads(json_match.group())
                return {
                    "success": True,
                    "acceptance_criteria": criteria,
                    "generated_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Could not parse acceptance criteria",
                    "raw_response": response_text
                }
                
        except Exception as e:
            logger.error(f"Error generating acceptance criteria: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def break_down_epic(self, epic_description: str,
                            target_users: str = "",
                            business_goals: str = "",
                            technical_constraints: str = "") -> Dict[str, Any]:
        """Break down an epic into user stories"""
        try:
            function = KernelFunctionFromPrompt(
                function_name="break_down_epic",
                prompt=self.epic_breakdown_prompt,
                prompt_template_config=PromptTemplateConfig(
                    input_variables=[
                        InputVariable(name="epic_description"),
                        InputVariable(name="target_users"),
                        InputVariable(name="business_goals"),
                        InputVariable(name="technical_constraints")
                    ]
                )
            )
            
            result = await self.kernel.invoke(
                function,
                epic_description=epic_description,
                target_users=target_users or "General users",
                business_goals=business_goals or "No specific goals provided",
                technical_constraints=technical_constraints or "No constraints specified"
            )
            
            response_text = str(result)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                breakdown = json.loads(json_match.group())
                return {
                    "success": True,
                    "breakdown": breakdown,
                    "generated_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Could not parse epic breakdown",
                    "raw_response": response_text
                }
                
        except Exception as e:
            logger.error(f"Error breaking down epic: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def estimate_story_points(self, stories: List[Dict]) -> Dict[str, Any]:
        """Estimate story points for a list of stories"""
        try:
            estimates = []
            
            for story in stories:
                # Simple heuristic-based estimation
                # In production, this would use ML models trained on historical data
                
                title = story.get("title", "")
                description = story.get("description", "")
                acceptance_criteria = story.get("acceptance_criteria", [])
                
                # Calculate complexity factors
                complexity_score = 0
                
                # Text length factor
                text_length = len(title) + len(description) + sum(len(ac) for ac in acceptance_criteria)
                if text_length > 500:
                    complexity_score += 3
                elif text_length > 200:
                    complexity_score += 2
                else:
                    complexity_score += 1
                
                # Number of acceptance criteria
                ac_count = len(acceptance_criteria)
                if ac_count > 8:
                    complexity_score += 3
                elif ac_count > 4:
                    complexity_score += 2
                else:
                    complexity_score += 1
                
                # Complexity keywords
                complexity_keywords = [
                    "integration", "api", "database", "migration", "security",
                    "performance", "complex", "multiple", "external", "new technology"
                ]
                
                full_text = (title + " " + description).lower()
                keyword_matches = sum(1 for keyword in complexity_keywords if keyword in full_text)
                complexity_score += keyword_matches
                
                # Map to Fibonacci sequence
                if complexity_score <= 3:
                    points = 1
                elif complexity_score <= 5:
                    points = 2
                elif complexity_score <= 8:
                    points = 3
                elif complexity_score <= 12:
                    points = 5
                elif complexity_score <= 16:
                    points = 8
                elif complexity_score <= 20:
                    points = 13
                else:
                    points = 21  # Consider splitting
                
                estimates.append({
                    "story": story.get("title", "Unknown"),
                    "estimated_points": points,
                    "complexity_score": complexity_score,
                    "reasoning": self._get_estimation_reasoning(complexity_score, points),
                    "recommendation": "Consider splitting" if points >= 13 else "Appropriate size"
                })
            
            return {
                "success": True,
                "estimates": estimates,
                "total_points": sum(est["estimated_points"] for est in estimates),
                "estimated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error estimating story points: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_estimation_reasoning(self, complexity_score: int, points: int) -> str:
        """Provide reasoning for story point estimation"""
        if points == 1:
            return "Simple story with clear requirements and minimal complexity"
        elif points == 2:
            return "Straightforward story with some minor complexity"
        elif points == 3:
            return "Moderate complexity requiring some design and implementation effort"
        elif points == 5:
            return "Complex story with multiple components or integration points"
        elif points == 8:
            return "Significant complexity with multiple unknowns or dependencies"
        elif points == 13:
            return "Very complex story that may benefit from being split into smaller stories"
        else:
            return "Extremely complex - strongly recommend breaking down into smaller stories"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Return information about this agent"""
        return {
            "name": self.agent_name,
            "type": "BacklogIntelligenceAgent",
            "capabilities": [
                "User story creation from requirements",
                "Backlog readiness analysis",
                "Acceptance criteria generation",
                "Epic breakdown into stories",
                "Story point estimation",
                "Dependency analysis"
            ],
            "description": "Specializes in product backlog management, user story creation, and ensuring stories are ready for development teams."
        }