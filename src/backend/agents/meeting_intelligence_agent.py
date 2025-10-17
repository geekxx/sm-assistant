"""
Meeting Intelligence Agent for Scrum Master Assistant
Specialized in meeting facilitation, transcript analysis, and action item extraction
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunctionFromPrompt
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

logger = logging.getLogger(__name__)

class MeetingIntelligenceAgent:
    """
    Meeting Intelligence Agent specialized in Scrum ceremony facilitation and analysis
    """
    
    def __init__(self, kernel: Kernel, deployment_name: str = "gpt-4.1"):
        self.kernel = kernel
        self.deployment_name = deployment_name
        self.agent_name = "SM-Asst-MeetingIntelligenceAgent"
        self._init_prompts()
        
    def _init_prompts(self):
        """Initialize prompt templates for meeting analysis capabilities"""
        
        self.meeting_analysis_prompt = """
        You are a Meeting Intelligence Agent specialized in Scrum ceremony facilitation and analysis.
        
        Analyze the following meeting transcript and extract key information:
        
        Meeting Type: {{$meeting_type}}
        Transcript: {{$transcript}}
        
        Provide a comprehensive analysis in JSON format with the following structure:
        {
            "meeting_summary": "Brief overview of the meeting",
            "action_items": [
                {
                    "description": "Action item description",
                    "owner": "Person responsible",
                    "due_date": "Estimated due date",
                    "priority": "High/Medium/Low"
                }
            ],
            "impediments": [
                {
                    "description": "Impediment description",
                    "affected_person": "Who is blocked",
                    "suggested_resolution": "Recommended action",
                    "severity": "Critical/High/Medium/Low"
                }
            ],
            "decisions": [
                {
                    "decision": "Decision made",
                    "context": "Why this decision was made",
                    "impact": "Expected impact"
                }
            ],
            "team_sentiment": {
                "overall_mood": "Positive/Neutral/Negative",
                "engagement_level": "High/Medium/Low",
                "observations": "Specific observations about team dynamics"
            },
            "follow_up_actions": [
                "Recommended follow-up actions"
            ],
            "ceremony_effectiveness": {
                "score": "1-10",
                "strengths": ["What went well"],
                "improvements": ["Suggested improvements"]
            }
        }
        """
        
        self.action_item_extraction_prompt = """
        You are specialized in extracting and structuring action items from meeting discussions.
        
        Text: {{$text}}
        
        Extract all action items and return in JSON format:
        {
            "action_items": [
                {
                    "id": "unique_identifier",
                    "description": "Clear action description",
                    "owner": "Person responsible (if mentioned)",
                    "due_date": "Due date (if mentioned) or 'Not specified'",
                    "priority": "High/Medium/Low based on context",
                    "category": "Sprint/Backlog/Process/Technical",
                    "dependencies": "Any mentioned dependencies"
                }
            ]
        }
        """
        
        self.impediment_detection_prompt = """
        You are specialized in identifying blockers and impediments in team discussions.
        
        Text: {{$text}}
        
        Identify all impediments and blockers mentioned, return in JSON format:
        {
            "impediments": [
                {
                    "id": "unique_identifier", 
                    "type": "Technical/Process/Resource/External",
                    "description": "Clear description of the impediment",
                    "affected_work": "What work is being blocked",
                    "affected_person": "Who is blocked",
                    "impact_level": "Critical/High/Medium/Low",
                    "suggested_resolution": "Recommended resolution approach",
                    "escalation_needed": true/false,
                    "estimated_resolution_time": "Time estimate if possible"
                }
            ]
        }
        """
        
        self.ceremony_facilitation_prompt = """
        You are facilitating a {{$ceremony_type}} ceremony. 
        
        Current Context:
        {{$context}}
        
        Provide facilitation guidance in JSON format:
        {
            "agenda": [
                {
                    "item": "Agenda item",
                    "duration": "Suggested time",
                    "purpose": "Why this is important"
                }
            ],
            "facilitation_tips": [
                "Specific tips for this ceremony"
            ],
            "questions_to_ask": [
                "Key questions to drive discussion"
            ],
            "success_criteria": [
                "How to know the ceremony was successful"
            ],
            "common_pitfalls": [
                "Things to watch out for"
            ]
        }
        """

    async def analyze_meeting_transcript(self, transcript: str, meeting_type: str = "Daily Standup") -> Dict[str, Any]:
        """
        Analyze a complete meeting transcript for comprehensive insights
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="analyze_meeting",
                prompt=self.meeting_analysis_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                meeting_type=meeting_type,
                transcript=transcript
            )
            
            analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "meeting_type": meeting_type,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in meeting analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def extract_action_items(self, text: str) -> Dict[str, Any]:
        """
        Extract structured action items from meeting text
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="extract_action_items",
                prompt=self.action_item_extraction_prompt
            )
            
            result = await self.kernel.invoke(function, text=text)
            action_items = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "action_items": action_items,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def detect_impediments(self, text: str) -> Dict[str, Any]:
        """
        Detect and categorize impediments from meeting discussions
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="detect_impediments",
                prompt=self.impediment_detection_prompt
            )
            
            result = await self.kernel.invoke(function, text=text)
            impediments = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "impediments": impediments,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error detecting impediments: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def facilitate_ceremony(self, ceremony_type: str, context: str = "") -> Dict[str, Any]:
        """
        Provide facilitation guidance for agile ceremonies
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="facilitate_ceremony",
                prompt=self.ceremony_facilitation_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                ceremony_type=ceremony_type,
                context=context
            )
            
            guidance = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "ceremony_type": ceremony_type,
                "guidance": guidance,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in ceremony facilitation: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def analyze_team_participation(self, transcript: str) -> Dict[str, Any]:
        """
        Analyze team participation patterns in meetings
        """
        try:
            participation_prompt = """
            Analyze team participation in this meeting transcript:
            
            {{$transcript}}
            
            Return analysis in JSON format:
            {
                "participation_summary": {
                    "total_speakers": "number of people who spoke",
                    "dominant_speakers": ["people who spoke most"],
                    "quiet_participants": ["people who spoke little or not at all"],
                    "balanced_discussion": true/false
                },
                "engagement_indicators": {
                    "question_count": "number of clarifying questions asked",
                    "interruptions": "instances of people talking over each other",
                    "positive_interactions": "supportive comments or agreements",
                    "tension_indicators": "signs of disagreement or frustration"
                },
                "recommendations": [
                    "Suggestions for improving participation"
                ]
            }
            """
            
            function = KernelFunctionFromPrompt(
                function_name="analyze_participation",
                prompt=participation_prompt
            )
            
            result = await self.kernel.invoke(function, transcript=transcript)
            analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "participation_analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing participation: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }