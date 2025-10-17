"""
Team Wellness Agent for Scrum Master Assistant
Specialized in team sentiment analysis, burnout detection, and engagement monitoring
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunctionFromPrompt

logger = logging.getLogger(__name__)

class TeamWellnessAgent:
    """
    Team Wellness Agent specialized in monitoring and supporting team health
    """
    
    def __init__(self, kernel: Kernel, deployment_name: str = "gpt-4o"):
        self.kernel = kernel
        self.deployment_name = deployment_name
        self.agent_name = "SM-Asst-TeamWellnessAgent"
        self._init_prompts()
        
    def _init_prompts(self):
        """Initialize prompt templates for team wellness analysis"""
        
        self.sentiment_analysis_prompt = """
        You are a Team Wellness Agent specialized in analyzing team communications for sentiment and wellness indicators.
        
        Analyze the following team communications for sentiment and wellness signals:
        
        Communications Data: {{$communications_data}}
        Time Period: {{$time_period}}
        
        Provide comprehensive analysis in JSON format:
        {
            "sentiment_analysis": {
                "overall_sentiment": "Positive/Neutral/Negative",
                "sentiment_score": "1-10 scale",
                "sentiment_trend": "Improving/Stable/Declining",
                "key_themes": ["Main themes in communications"],
                "positive_indicators": ["Signs of good team health"],
                "concern_indicators": ["Signs requiring attention"]
            },
            "engagement_metrics": {
                "participation_level": "High/Medium/Low",
                "response_time": "Fast/Average/Slow team responsiveness",
                "collaboration_quality": "Strong/Moderate/Weak collaboration signals",
                "initiative_taking": "Frequency of proactive contributions"
            },
            "wellbeing_indicators": {
                "stress_signals": ["Indicators of team stress"],
                "burnout_risk_factors": ["Early warning signs of burnout"],
                "work_life_balance": "Assessment of balance indicators",
                "support_needs": ["Areas where team needs support"]
            },
            "individual_insights": [
                {
                    "team_member": "Anonymous identifier (maintain privacy)",
                    "wellness_score": "1-10",
                    "key_observations": "Observations about individual wellness",
                    "recommended_actions": "Suggested support actions"
                }
            ],
            "recommendations": [
                "Specific actions to improve team wellness"
            ]
        }
        """
        
        self.burnout_detection_prompt = """
        You are specialized in detecting early warning signs of team burnout.
        
        Team Data: {{$team_data}}
        Recent Activity: {{$recent_activity}}
        
        Analyze for burnout risks and provide assessment in JSON format:
        {
            "burnout_assessment": {
                "overall_risk_level": "Critical/High/Medium/Low",
                "risk_factors": [
                    {
                        "factor": "Specific risk factor",
                        "severity": "Critical/High/Medium/Low",
                        "evidence": "Evidence supporting this risk",
                        "affected_members": "Number or percentage affected"
                    }
                ],
                "early_warning_signs": [
                    "Specific warning signs detected"
                ],
                "protective_factors": [
                    "Positive factors that reduce burnout risk"
                ]
            },
            "intervention_recommendations": [
                {
                    "intervention": "Recommended intervention",
                    "urgency": "Immediate/Soon/Planned",
                    "target": "Individual/Team/Process",
                    "expected_outcome": "Expected positive impact"
                }
            ],
            "monitoring_suggestions": [
                "Ways to continue monitoring team health"
            ]
        }
        """
        
        self.team_dynamics_prompt = """
        You are analyzing team dynamics and collaboration patterns.
        
        Team Interaction Data: {{$interaction_data}}
        
        Analyze team dynamics and provide insights in JSON format:
        {
            "team_dynamics": {
                "collaboration_patterns": {
                    "communication_frequency": "Analysis of how often team communicates",
                    "cross_functional_cooperation": "Quality of cooperation across roles",
                    "knowledge_sharing": "How well team shares knowledge",
                    "conflict_resolution": "How team handles disagreements"
                },
                "trust_indicators": {
                    "psychological_safety": "High/Medium/Low psychological safety",
                    "openness": "Willingness to share concerns and ideas",
                    "support_patterns": "How team members support each other",
                    "feedback_culture": "Quality of feedback exchange"
                },
                "team_cohesion": {
                    "unity_score": "1-10 scale",
                    "shared_purpose": "Alignment on team goals",
                    "mutual_respect": "Evidence of respect among members",
                    "inclusive_behavior": "How well team includes all members"
                }
            },
            "improvement_opportunities": [
                "Specific areas for improving team dynamics"
            ],
            "celebration_opportunities": [
                "Achievements and positive behaviors to recognize"
            ]
        }
        """

    async def analyze_team_sentiment(self, communications_data: str, time_period: str = "Last 2 weeks") -> Dict[str, Any]:
        """
        Analyze team sentiment from communications data
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="analyze_sentiment",
                prompt=self.sentiment_analysis_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                communications_data=communications_data,
                time_period=time_period
            )
            
            analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "sentiment_analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def detect_burnout_risk(self, team_data: str, recent_activity: str = "") -> Dict[str, Any]:
        """
        Detect early warning signs of team burnout
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="detect_burnout",
                prompt=self.burnout_detection_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                team_data=team_data,
                recent_activity=recent_activity
            )
            
            assessment = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "burnout_assessment": assessment,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in burnout detection: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def analyze_team_dynamics(self, interaction_data: str) -> Dict[str, Any]:
        """
        Analyze team collaboration patterns and dynamics
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="analyze_dynamics",
                prompt=self.team_dynamics_prompt
            )
            
            result = await self.kernel.invoke(function, interaction_data=interaction_data)
            analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "team_dynamics": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing team dynamics: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def generate_wellness_report(self, team_id: str, period: str = "sprint") -> Dict[str, Any]:
        """
        Generate comprehensive team wellness report
        """
        try:
            # This would typically gather data from multiple sources
            # For demonstration, providing a structured response
            
            report_prompt = """
            Generate a comprehensive team wellness report for the current {{$period}}.
            
            Provide a detailed wellness report in JSON format:
            {
                "wellness_summary": {
                    "overall_health_score": "1-10 scale",
                    "key_findings": ["Main wellness insights"],
                    "trend_analysis": "Improvement/Stable/Declining trends"
                },
                "recommendations": {
                    "immediate_actions": ["Actions needed right away"],
                    "short_term_goals": ["Goals for next 1-2 weeks"],
                    "long_term_initiatives": ["Longer-term wellness initiatives"]
                },
                "monitoring_plan": {
                    "key_metrics": ["Metrics to continue tracking"],
                    "check_in_frequency": "Recommended check-in schedule",
                    "early_warning_signs": ["Signs to watch for"]
                }
            }
            """
            
            function = KernelFunctionFromPrompt(
                function_name="generate_wellness_report",
                prompt=report_prompt
            )
            
            result = await self.kernel.invoke(function, period=period)
            report = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "team_id": team_id,
                "period": period,
                "wellness_report": report,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating wellness report: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def recommend_interventions(self, wellness_data: str) -> Dict[str, Any]:
        """
        Recommend specific interventions based on wellness analysis
        """
        try:
            intervention_prompt = """
            Based on the following team wellness data, recommend specific interventions:
            
            Wellness Data: {{$wellness_data}}
            
            Provide intervention recommendations in JSON format:
            {
                "intervention_plan": {
                    "immediate_interventions": [
                        {
                            "intervention": "Specific intervention",
                            "target": "Individual/Team/Process",
                            "priority": "Critical/High/Medium",
                            "implementation": "How to implement",
                            "success_metrics": "How to measure success"
                        }
                    ],
                    "preventive_measures": [
                        "Measures to prevent wellness issues"
                    ],
                    "team_building_activities": [
                        "Suggested team building approaches"
                    ],
                    "process_improvements": [
                        "Process changes to support wellness"
                    ]
                }
            }
            """
            
            function = KernelFunctionFromPrompt(
                function_name="recommend_interventions", 
                prompt=intervention_prompt
            )
            
            result = await self.kernel.invoke(function, wellness_data=wellness_data)
            recommendations = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "intervention_recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recommending interventions: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }