"""
Flow Metrics Agent for Scrum Master Assistant
Specialized in delivery analytics, bottleneck identification, and flow optimization
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelFunctionFromPrompt

logger = logging.getLogger(__name__)

class FlowMetricsAgent:
    """
    Flow Metrics Agent specialized in analyzing team delivery performance
    """
    
    def __init__(self, kernel: Kernel, deployment_name: str = "gpt-4.1"):
        self.kernel = kernel
        self.deployment_name = deployment_name
        self.agent_name = "SM-Asst-FlowMetricsAgent"
        self._init_prompts()
        
    def _init_prompts(self):
        """Initialize prompt templates for flow metrics analysis"""
        
        self.flow_analysis_prompt = """
        You are a Flow Metrics Agent specialized in analyzing team delivery performance.
        
        Analyze the following work item data and calculate flow metrics:
        
        Work Items Data: {{$work_items_data}}
        Sprint Information: {{$sprint_info}}
        
        Calculate and provide analysis in JSON format:
        {
            "flow_metrics": {
                "cycle_time": {
                    "average_days": "Average cycle time in days",
                    "median_days": "Median cycle time in days", 
                    "trend": "Improving/Stable/Degrading",
                    "analysis": "Analysis of cycle time patterns"
                },
                "lead_time": {
                    "average_days": "Average lead time in days",
                    "median_days": "Median lead time in days",
                    "trend": "Improving/Stable/Degrading", 
                    "analysis": "Analysis of lead time patterns"
                },
                "throughput": {
                    "items_per_sprint": "Average items completed per sprint",
                    "story_points_per_sprint": "Average story points per sprint",
                    "trend": "Improving/Stable/Degrading",
                    "analysis": "Analysis of throughput patterns"
                },
                "work_in_progress": {
                    "average_wip": "Average work in progress",
                    "wip_limit_adherence": "Percentage of time WIP limits were respected",
                    "recommendations": "WIP optimization recommendations"
                }
            },
            "bottlenecks": [
                {
                    "stage": "Development stage with bottleneck",
                    "description": "Description of the bottleneck",
                    "impact": "Impact on flow",
                    "suggested_resolution": "Recommended resolution"
                }
            ],
            "predictability": {
                "delivery_consistency": "High/Medium/Low",
                "forecast_accuracy": "Percentage accuracy of previous forecasts",
                "risk_factors": ["Factors affecting predictability"]
            },
            "coaching_insights": [
                "Specific coaching recommendations based on metrics"
            ]
        }
        """
        
        self.bottleneck_analysis_prompt = """
        You are specialized in identifying delivery bottlenecks from flow data.
        
        Flow Data: {{$flow_data}}
        
        Identify bottlenecks and provide recommendations in JSON format:
        {
            "bottleneck_analysis": {
                "identified_bottlenecks": [
                    {
                        "location": "Where the bottleneck occurs",
                        "type": "Resource/Process/Skill/Dependency",
                        "severity": "Critical/High/Medium/Low",
                        "evidence": "Data supporting this bottleneck",
                        "impact": "How it affects delivery",
                        "root_causes": ["Potential root causes"],
                        "resolution_strategies": ["Recommended solutions"]
                    }
                ],
                "flow_efficiency": {
                    "percentage": "Percentage of time work is actively being worked on",
                    "wait_time_analysis": "Analysis of wait times between stages",
                    "optimization_opportunities": ["Opportunities to improve efficiency"]
                }
            }
        }
        """
        
        self.forecasting_prompt = """
        You are specialized in delivery forecasting based on historical flow metrics.
        
        Historical Data: {{$historical_data}}
        Upcoming Work: {{$upcoming_work}}
        
        Provide forecasting analysis in JSON format:
        {
            "delivery_forecast": {
                "sprint_capacity": {
                    "estimated_story_points": "Expected story points for next sprint",
                    "estimated_items": "Expected number of items",
                    "confidence_level": "High/Medium/Low confidence in estimate"
                },
                "release_forecast": {
                    "remaining_work": "Estimated remaining work",
                    "projected_completion": "Projected completion date range",
                    "risk_factors": ["Factors that could affect timeline"],
                    "scenario_analysis": {
                        "best_case": "Optimistic timeline",
                        "most_likely": "Most probable timeline", 
                        "worst_case": "Conservative timeline"
                    }
                },
                "recommendations": [
                    "Specific recommendations for improving predictability"
                ]
            }
        }
        """

    async def analyze_flow_metrics(self, work_items_data: str, sprint_info: str = "") -> Dict[str, Any]:
        """
        Analyze flow metrics from work item data
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="analyze_flow",
                prompt=self.flow_analysis_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                work_items_data=work_items_data,
                sprint_info=sprint_info
            )
            
            analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in flow metrics analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def identify_bottlenecks(self, flow_data: str) -> Dict[str, Any]:
        """
        Identify and analyze delivery bottlenecks
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="identify_bottlenecks",
                prompt=self.bottleneck_analysis_prompt
            )
            
            result = await self.kernel.invoke(function, flow_data=flow_data)
            analysis = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "bottleneck_analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def generate_forecast(self, historical_data: str, upcoming_work: str = "") -> Dict[str, Any]:
        """
        Generate delivery forecasts based on historical performance
        """
        try:
            function = KernelFunctionFromPrompt(
                function_name="generate_forecast",
                prompt=self.forecasting_prompt
            )
            
            result = await self.kernel.invoke(
                function,
                historical_data=historical_data,
                upcoming_work=upcoming_work
            )
            
            forecast = json.loads(str(result))
            
            return {
                "success": True,
                "agent": self.agent_name,
                "forecast": forecast,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }

    async def calculate_key_metrics(self, work_items: List[Dict]) -> Dict[str, Any]:
        """
        Calculate key flow metrics from work item data
        """
        try:
            # Simplified calculation for demonstration
            if not work_items:
                return {
                    "success": False,
                    "error": "No work items provided",
                    "agent": self.agent_name
                }
            
            # Calculate basic metrics
            cycle_times = []
            lead_times = []
            throughput_count = len([item for item in work_items if item.get('status') == 'Done'])
            
            for item in work_items:
                if item.get('start_date') and item.get('end_date'):
                    start = datetime.fromisoformat(item['start_date'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(item['end_date'].replace('Z', '+00:00'))
                    cycle_time = (end - start).days
                    cycle_times.append(cycle_time)
                
                if item.get('created_date') and item.get('end_date'):
                    created = datetime.fromisoformat(item['created_date'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(item['end_date'].replace('Z', '+00:00'))
                    lead_time = (end - created).days
                    lead_times.append(lead_time)
            
            avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0
            avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0
            
            return {
                "success": True,
                "agent": self.agent_name,
                "metrics": {
                    "average_cycle_time_days": round(avg_cycle_time, 2),
                    "average_lead_time_days": round(avg_lead_time, 2),
                    "throughput_items": throughput_count,
                    "total_items_analyzed": len(work_items),
                    "completion_rate": round(throughput_count / len(work_items) * 100, 2)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }