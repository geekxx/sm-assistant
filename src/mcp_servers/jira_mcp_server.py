"""
Jira MCP Server for Scrum Master Assistant
Provides integration with Atlassian Jira for backlog and project management.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jira-mcp-server")

class JiraMCPServer:
    def __init__(self, jira_url: str, email: str, api_token: str):
        self.jira_url = jira_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.server = Server("jira-scrum-assistant")
        self.client = None
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available Jira tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="get_backlog_items",
                    description="Get backlog items from a Jira project with filtering options",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {"type": "string", "description": "Jira project key"},
                            "status": {"type": "string", "description": "Filter by status (e.g., 'To Do', 'In Progress')"},
                            "assignee": {"type": "string", "description": "Filter by assignee email"},
                            "story_points": {"type": "integer", "description": "Filter by story points"},
                            "limit": {"type": "integer", "description": "Maximum number of items to return", "default": 50}
                        },
                        "required": ["project_key"]
                    }
                ),
                types.Tool(
                    name="create_user_story",
                    description="Create a new user story in Jira",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {"type": "string", "description": "Jira project key"},
                            "summary": {"type": "string", "description": "Story title/summary"},
                            "description": {"type": "string", "description": "Story description including acceptance criteria"},
                            "story_points": {"type": "integer", "description": "Story point estimation"},
                            "priority": {"type": "string", "description": "Priority level (Highest, High, Medium, Low, Lowest)"},
                            "assignee": {"type": "string", "description": "Assignee email"},
                            "labels": {"type": "array", "items": {"type": "string"}, "description": "Labels for the story"},
                            "epic_link": {"type": "string", "description": "Epic key to link this story to"}
                        },
                        "required": ["project_key", "summary", "description"]
                    }
                ),
                types.Tool(
                    name="get_sprint_data",
                    description="Get current or recent sprint information including burndown data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "board_id": {"type": "integer", "description": "Jira board ID"},
                            "state": {"type": "string", "description": "Sprint state: 'active', 'closed', 'future'", "default": "active"}
                        },
                        "required": ["board_id"]
                    }
                ),
                types.Tool(
                    name="get_flow_metrics",
                    description="Calculate flow metrics like cycle time, lead time for stories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {"type": "string", "description": "Jira project key"},
                            "days_back": {"type": "integer", "description": "Number of days to look back", "default": 30},
                            "issue_type": {"type": "string", "description": "Issue type to analyze (Story, Bug, Task)", "default": "Story"}
                        },
                        "required": ["project_key"]
                    }
                ),
                types.Tool(
                    name="update_story_status",
                    description="Update the status of a story (move through workflow)",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "issue_key": {"type": "string", "description": "Jira issue key (e.g., PROJ-123)"},
                            "transition": {"type": "string", "description": "Transition name (e.g., 'Start Progress', 'Done')"}
                        },
                        "required": ["issue_key", "transition"]
                    }
                ),
                types.Tool(
                    name="add_story_comment",
                    description="Add a comment to a Jira story",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {"type": "string", "description": "Jira issue key"},
                            "comment": {"type": "string", "description": "Comment text"},
                            "visibility": {"type": "string", "description": "Comment visibility (public, internal)", "default": "public"}
                        },
                        "required": ["issue_key", "comment"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            try:
                if name == "get_backlog_items":
                    result = await self._get_backlog_items(**arguments)
                elif name == "create_user_story":
                    result = await self._create_user_story(**arguments)
                elif name == "get_sprint_data":
                    result = await self._get_sprint_data(**arguments)
                elif name == "get_flow_metrics":
                    result = await self._get_flow_metrics(**arguments)
                elif name == "update_story_status":
                    result = await self._update_story_status(**arguments)
                elif name == "add_story_comment":
                    result = await self._add_story_comment(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_client(self):
        """Get or create HTTP client with authentication"""
        if not self.client:
            auth = httpx.BasicAuth(self.email, self.api_token)
            self.client = httpx.AsyncClient(
                base_url=f"{self.jira_url}/rest/api/3",
                auth=auth,
                timeout=30.0
            )
        return self.client

    async def _get_backlog_items(self, project_key: str, status: Optional[str] = None, 
                                assignee: Optional[str] = None, story_points: Optional[int] = None, 
                                limit: int = 50) -> Dict[str, Any]:
        """Get backlog items with filtering"""
        client = await self._get_client()
        
        # Build JQL query
        jql_parts = [f"project = {project_key}", "issuetype in (Story, Task, Bug)"]
        
        if status:
            jql_parts.append(f"status = '{status}'")
        if assignee:
            jql_parts.append(f"assignee = '{assignee}'")
        if story_points:
            jql_parts.append(f"'Story Points' = {story_points}")
        
        jql = " AND ".join(jql_parts)
        
        params = {
            "jql": jql,
            "maxResults": limit,
            "fields": "summary,description,status,assignee,priority,labels,created,updated,customfield_10016", # Story Points
            "expand": "changelog"
        }
        
        response = await client.get("/search", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Process and enrich the data
        processed_issues = []
        for issue in data["issues"]:
            processed_issue = {
                "key": issue["key"],
                "summary": issue["fields"]["summary"],
                "description": issue["fields"]["description"],
                "status": issue["fields"]["status"]["name"],
                "assignee": issue["fields"]["assignee"]["displayName"] if issue["fields"]["assignee"] else None,
                "priority": issue["fields"]["priority"]["name"],
                "labels": issue["fields"]["labels"],
                "created": issue["fields"]["created"],
                "updated": issue["fields"]["updated"],
                "story_points": issue["fields"].get("customfield_10016"), # Story Points
                "url": f"{self.jira_url}/browse/{issue['key']}"
            }
            processed_issues.append(processed_issue)
        
        return {
            "issues": processed_issues,
            "total": data["total"],
            "query": jql
        }

    async def _create_user_story(self, project_key: str, summary: str, description: str, 
                                story_points: Optional[int] = None, priority: str = "Medium",
                                assignee: Optional[str] = None, labels: Optional[List[str]] = None, 
                                epic_link: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user story"""
        client = await self._get_client()
        
        # Build issue data
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Story"},
                "priority": {"name": priority}
            }
        }
        
        if story_points:
            issue_data["fields"]["customfield_10016"] = story_points  # Story Points
        if assignee:
            issue_data["fields"]["assignee"] = {"emailAddress": assignee}
        if labels:
            issue_data["fields"]["labels"] = [{"name": label} for label in labels]
        if epic_link:
            issue_data["fields"]["customfield_10014"] = epic_link  # Epic Link
        
        response = await client.post("/issue", json=issue_data)
        response.raise_for_status()
        
        created_issue = response.json()
        return {
            "key": created_issue["key"],
            "id": created_issue["id"],
            "url": f"{self.jira_url}/browse/{created_issue['key']}",
            "summary": summary
        }

    async def _get_sprint_data(self, board_id: int, state: str = "active") -> Dict[str, Any]:
        """Get sprint information and burndown data"""
        client = await self._get_client()
        
        # Get sprints for the board
        response = await client.get(f"/board/{board_id}/sprint", params={"state": state})
        response.raise_for_status()
        
        sprints_data = response.json()
        
        if not sprints_data["values"]:
            return {"message": f"No {state} sprints found", "sprints": []}
        
        sprint = sprints_data["values"][0]  # Get the first sprint
        
        # Get sprint issues
        issues_response = await client.get(f"/sprint/{sprint['id']}/issue")
        issues_response.raise_for_status()
        
        issues = issues_response.json()["issues"]
        
        # Calculate sprint metrics
        total_points = sum(issue["fields"].get("customfield_10016", 0) or 0 for issue in issues)
        completed_points = sum(
            issue["fields"].get("customfield_10016", 0) or 0 
            for issue in issues 
            if issue["fields"]["status"]["statusCategory"]["key"] == "done"
        )
        
        return {
            "sprint": {
                "id": sprint["id"],
                "name": sprint["name"],
                "state": sprint["state"],
                "startDate": sprint.get("startDate"),
                "endDate": sprint.get("endDate"),
                "goal": sprint.get("goal")
            },
            "metrics": {
                "total_issues": len(issues),
                "total_story_points": total_points,
                "completed_story_points": completed_points,
                "completion_percentage": (completed_points / total_points * 100) if total_points > 0 else 0
            },
            "issues": [
                {
                    "key": issue["key"],
                    "summary": issue["fields"]["summary"],
                    "status": issue["fields"]["status"]["name"],
                    "story_points": issue["fields"].get("customfield_10016")
                }
                for issue in issues
            ]
        }

    async def _get_flow_metrics(self, project_key: str, days_back: int = 30, 
                               issue_type: str = "Story") -> Dict[str, Any]:
        """Calculate flow metrics for completed issues"""
        client = await self._get_client()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        jql = f"project = {project_key} AND issuetype = {issue_type} AND status = Done AND resolved >= '{start_date.strftime('%Y-%m-%d')}'"
        
        params = {
            "jql": jql,
            "maxResults": 100,
            "fields": "created,resolutiondate,status",
            "expand": "changelog"
        }
        
        response = await client.get("/search", params=params)
        response.raise_for_status()
        
        issues = response.json()["issues"]
        
        # Calculate metrics
        cycle_times = []
        lead_times = []
        
        for issue in issues:
            created = datetime.fromisoformat(issue["fields"]["created"].replace('Z', '+00:00'))
            resolved = datetime.fromisoformat(issue["fields"]["resolutiondate"].replace('Z', '+00:00'))
            
            # Find when work started (In Progress transition)
            work_started = created
            if issue.get("changelog"):
                for history in issue["changelog"]["histories"]:
                    for item in history["items"]:
                        if item["field"] == "status" and "In Progress" in item.get("toString", ""):
                            work_started = datetime.fromisoformat(history["created"].replace('Z', '+00:00'))
                            break
            
            lead_time = (resolved - created).total_seconds() / 86400  # Convert to days
            cycle_time = (resolved - work_started).total_seconds() / 86400
            
            lead_times.append(lead_time)
            cycle_times.append(cycle_time)
        
        def percentile(data, p):
            if not data:
                return 0
            sorted_data = sorted(data)
            k = (len(sorted_data) - 1) * p / 100
            f = int(k)
            c = k - f
            if f == len(sorted_data) - 1:
                return sorted_data[f]
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
        
        return {
            "period": f"{days_back} days",
            "total_completed_issues": len(issues),
            "throughput": len(issues) / (days_back / 7),  # Issues per week
            "lead_time": {
                "average": sum(lead_times) / len(lead_times) if lead_times else 0,
                "p50": percentile(lead_times, 50),
                "p85": percentile(lead_times, 85),
                "p95": percentile(lead_times, 95)
            },
            "cycle_time": {
                "average": sum(cycle_times) / len(cycle_times) if cycle_times else 0,
                "p50": percentile(cycle_times, 50),
                "p85": percentile(cycle_times, 85),
                "p95": percentile(cycle_times, 95)
            }
        }

    async def _update_story_status(self, issue_key: str, transition: str) -> Dict[str, Any]:
        """Update story status by transitioning through workflow"""
        client = await self._get_client()
        
        # Get available transitions for the issue
        transitions_response = await client.get(f"/issue/{issue_key}/transitions")
        transitions_response.raise_for_status()
        
        available_transitions = transitions_response.json()["transitions"]
        
        # Find the transition ID by name
        transition_id = None
        for trans in available_transitions:
            if trans["name"].lower() == transition.lower():
                transition_id = trans["id"]
                break
        
        if not transition_id:
            available_names = [t["name"] for t in available_transitions]
            return {
                "error": f"Transition '{transition}' not found. Available transitions: {available_names}"
            }
        
        # Execute the transition
        transition_data = {
            "transition": {"id": transition_id}
        }
        
        response = await client.post(f"/issue/{issue_key}/transitions", json=transition_data)
        response.raise_for_status()
        
        return {
            "success": True,
            "issue_key": issue_key,
            "transition": transition,
            "message": f"Successfully transitioned {issue_key} to {transition}"
        }

    async def _add_story_comment(self, issue_key: str, comment: str, 
                                visibility: str = "public") -> Dict[str, Any]:
        """Add a comment to a story"""
        client = await self._get_client()
        
        comment_data = {
            "body": comment
        }
        
        # Add visibility restriction if needed
        if visibility == "internal":
            comment_data["visibility"] = {
                "type": "role",
                "value": "Developers"
            }
        
        response = await client.post(f"/issue/{issue_key}/comment", json=comment_data)
        response.raise_for_status()
        
        created_comment = response.json()
        return {
            "id": created_comment["id"],
            "issue_key": issue_key,
            "comment": comment,
            "created": created_comment["created"],
            "author": created_comment["author"]["displayName"]
        }

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="jira-scrum-assistant",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

async def main():
    import os
    
    # Get configuration from environment variables
    jira_url = os.getenv("JIRA_URL", "https://your-company.atlassian.net")
    email = os.getenv("JIRA_EMAIL", "your-email@company.com")
    api_token = os.getenv("JIRA_API_TOKEN", "your-api-token")
    
    if not all([jira_url, email, api_token]):
        logger.error("Missing required environment variables: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN")
        return
    
    server = JiraMCPServer(jira_url, email, api_token)
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())