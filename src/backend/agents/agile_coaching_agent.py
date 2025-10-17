"""
Agile Coaching Agent for Scrum Master Assistant
Strategic agent that synthesizes insights from all other agents
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunctionFromPrompt

logger = logging.getLogger(__name__)

class AgileCoachingAgent:
    """
    Agile Coaching Agent that provides strategic guidance by synthesizing insights
    """
    
    def __init__(self, kernel: Kernel, deployment_name: str = "gpt-4.1"):
        self.kernel = kernel
        self.deployment_name = deployment_name
        self.agent_name = "SM-Asst-AgileCoachingAgent"
        self._init_prompts()
        
    def _init_prompts(self):
        """Initialize prompt templates for agile coaching capabilities"""
        
        self.coaching_synthesis_prompt = """
        You are an Agile Coaching Agent that provides strategic guidance by synthesizing insights from specialized agents.
        
        Agent Insights:
        - Backlog Intelligence: {{$backlog_insights}}
        - Meeting Intelligence: {{$meeting_insights}}
        - Flow Metrics: {{$flow_insights}}
        - Team Wellness: {{$wellness_insights}}
        
        Team Context: {{$team_context}}
        
        Provide comprehensive coaching guidance in JSON format:
        {
            "holistic_assessment": {
                "team_maturity_level": "Beginning/Developing/Proficient/Advanced",
                "key_strengths": ["Areas where team excels"],
                "improvement_areas": ["Areas needing attention"],
                "critical_issues": ["Issues requiring immediate attention"],
                "overall_health": "Overall team health assessment"
            },
            "strategic_recommendations": [
                {
                    "recommendation": "Strategic recommendation",
                    "priority": "Critical/High/Medium/Low",
                    "rationale": "Why this recommendation is important",
                    "expected_impact": "Expected positive outcomes",
                    "implementation_approach": "How to implement this",
                    "success_metrics": "How to measure success",
                    "timeline": "Suggested implementation timeline"
                }
            ],
            "process_optimization": {
                "ceremony_improvements": ["Suggestions for improving agile ceremonies"],
                "workflow_enhancements": ["Process improvements for better flow"],
                "communication_improvements": ["Ways to enhance team communication"],
                "collaboration_tools": ["Tool or technique recommendations"]
            },
            "coaching_plan": {
                "individual_coaching_needs": ["Individual development areas"],
                "team_coaching_focus": ["Team-level coaching priorities"],
                "skill_development": ["Skills the team should develop"],
                "learning_opportunities": ["Suggested learning initiatives"]
            },
            "escalation_items": [
                "Issues that require human Scrum Master intervention"
            ]
        }
        """
        
        self.process_optimization_prompt = """
        You are providing agile process optimization guidance.
        
        Current Process Data: {{$process_data}}
        Performance Metrics: {{$metrics}}
        Team Feedback: {{$feedback}}
        
        Analyze and provide optimization recommendations in JSON format:
        {
            "process_analysis": {
                "current_effectiveness": "Assessment of current process effectiveness",
                "identified_waste": ["Types of waste identified in current process"],
                "value_stream_insights": ["Insights about value delivery"],
                "bottleneck_patterns": ["Recurring bottleneck patterns"]
            },
            "optimization_recommendations": [
                {
                    "area": "Process area to optimize",
                    "current_state": "Description of current state",
                    "proposed_improvement": "Specific improvement proposal",
                    "implementation_steps": ["Step-by-step implementation"],
                    "expected_benefits": ["Expected benefits"],
                    "risks": ["Potential risks and mitigation"],
                    "pilot_approach": "How to pilot this change"
                }
            ],
            "change_management": {
                "stakeholder_communication": "How to communicate changes",
                "training_needs": ["Training required for changes"],
                "adoption_strategy": "Strategy for change adoption",
                "feedback_mechanisms": ["Ways to gather feedback on changes"]
            }
        }
        """
        
        self.team_development_prompt = """
        You are providing team development coaching.
        
        Team Assessment: {{$team_assessment}}
        Development Goals: {{$development_goals}}
        
        Provide team development guidance in JSON format:
        {
            "development_plan": {
                "current_capabilities": ["Team's current strengths"],
                "skill_gaps": ["Areas where team needs development"],
                "growth_opportunities": ["Opportunities for team growth"],
                "development_priorities": ["Priority areas for development"]
            },
            "coaching_strategies": [
                {
                    "focus_area": "Area of focus",
                    "coaching_approach": "Recommended coaching method",
                    "activities": ["Specific activities or exercises"],
                    "timeline": "Suggested timeline",
                    "success_indicators": ["How to know if coaching is working"]
                }
            ],
            "learning_initiatives": [
                {
                    "topic": "Learning topic",
                    "format": "Workshop/Training/Self-study/Mentoring",
                    "provider": "Internal/External provider suggestion",
                    "priority": "High/Medium/Low",
                    "expected_outcome": "Expected learning outcome"
                }
            ],
            "mentoring_recommendations": [
                "Mentoring opportunities within or outside the team"
            ]
        }
        """

    async def synthesize_coaching_insights(self, agent_insights: Dict[str, Any], team_context: str = "") -> Dict[str, Any]:
        """
        Synthesize insights from all agents to provide holistic coaching guidance
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="synthesize_insights",
                prompt=self.coaching_synthesis_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                backlog_insights=json.dumps(agent_insights.get('backlog', {})),
                meeting_insights=json.dumps(agent_insights.get('meeting', {})),
                flow_insights=json.dumps(agent_insights.get('flow', {})),
                wellness_insights=json.dumps(agent_insights.get('wellness', {})),
                team_context=team_context
            )
            
            coaching_guidance = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "coaching_guidance": coaching_guidance,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing coaching insights: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def optimize_processes(self, process_data: str, metrics: str = "", feedback: str = "") -> Dict[str, Any]:
        """
        Provide process optimization recommendations
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="optimize_processes",
                prompt=self.process_optimization_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                process_data=process_data,
                metrics=metrics,
                feedback=feedback
            )
            
            optimization = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "process_optimization": optimization,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in process optimization: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def develop_team_coaching_plan(self, team_assessment: str, development_goals: str = "") -> Dict[str, Any]:
        """
        Create comprehensive team development coaching plan
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="develop_coaching_plan",
                prompt=self.team_development_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                team_assessment=team_assessment,
                development_goals=development_goals
            )
            
            development_plan = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "development_plan": development_plan,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error developing coaching plan: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def generate_sprint_coaching_summary(self, sprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive sprint coaching summary
        """
        try:
            summary_prompt = """
            Generate a comprehensive sprint coaching summary based on all available data.
            
            Sprint Data: {{$sprint_data}}
            
            Provide coaching summary in JSON format:
            {
                "sprint_overview": {
                    "sprint_health": "Overall assessment of sprint health",
                    "key_achievements": ["Major accomplishments this sprint"],
                    "challenges_encountered": ["Key challenges faced"],
                    "lessons_learned": ["Important lessons from this sprint"]
                },
                "performance_analysis": {
                    "velocity_assessment": "Analysis of team velocity",
                    "quality_indicators": "Assessment of work quality",
                    "collaboration_effectiveness": "How well team collaborated",
                    "goal_achievement": "Assessment of sprint goal achievement"
                },
                "coaching_recommendations": {
                    "immediate_actions": ["Actions for next sprint"],
                    "process_adjustments": ["Process improvements to try"],
                    "team_development": ["Team development opportunities"],
                    "celebration_items": ["Things to celebrate and recognize"]
                },
                "next_sprint_focus": [
                    "Key focus areas for the upcoming sprint"
                ]
            }
            """
            
            function = KernelFunctionFromPrompt(
                function_name="generate_sprint_summary",
                prompt=summary_prompt
            )
            
            result = await self.kernel.invoke(function, sprint_data=json.dumps(sprint_data))
            summary = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "sprint_coaching_summary": summary,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating sprint summary: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def identify_escalation_needs(self, all_agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify issues that require human Scrum Master intervention
        """
        try:
            escalation_prompt = """
            Analyze all agent data to identify issues requiring human Scrum Master escalation.
            
            Agent Data: {{$agent_data}}
            
            Identify escalation needs in JSON format:
            {
                "escalation_analysis": {
                    "critical_issues": [
                        {
                            "issue": "Description of critical issue",
                            "severity": "Critical/High/Medium",
                            "impact": "Potential impact if not addressed",
                            "recommended_action": "Suggested escalation action",
                            "urgency": "Immediate/Today/This Week",
                            "stakeholders": ["Who should be involved"]
                        }
                    ],
                    "patterns_requiring_attention": [
                        "Patterns that suggest need for human intervention"
                    ],
                    "coaching_limitations": [
                        "Areas where AI coaching has limitations"
                    ]
                },
                "escalation_plan": {
                    "immediate_escalations": ["Issues needing immediate attention"],
                    "planned_discussions": ["Items for next coaching conversation"],
                    "monitoring_items": ["Items to monitor before escalating"]
                }
            }
            """
            
            function = KernelFunctionFromPrompt(
                function_name="identify_escalations",
                prompt=escalation_prompt
            )
            
            result = await self.kernel.invoke(function, agent_data=json.dumps(all_agent_data))
            escalation_analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "escalation_analysis": escalation_analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error identifying escalation needs: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }