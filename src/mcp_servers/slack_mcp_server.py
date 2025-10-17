"""
Slack MCP Server for Scrum Master Assistant
Provides integration with Slack for team communication analysis and notifications.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slack-mcp-server")

class SlackMCPServer:
    def __init__(self, bot_token: str, app_token: Optional[str] = None):
        self.bot_token = bot_token
        self.app_token = app_token
        self.server = Server("slack-scrum-assistant")
        self.client = AsyncWebClient(token=bot_token)
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available Slack tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="analyze_channel_sentiment",
                    description="Analyze sentiment and engagement patterns in a Slack channel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string", "description": "Channel name or ID"},
                            "days_back": {"type": "integer", "description": "Number of days to analyze", "default": 7},
                            "include_threads": {"type": "boolean", "description": "Include thread replies", "default": True}
                        },
                        "required": ["channel"]
                    }
                ),
                types.Tool(
                    name="detect_team_blockers",
                    description="Detect mentions of blockers, impediments, or issues in team channels",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channels": {"type": "array", "items": {"type": "string"}, "description": "List of channel names or IDs"},
                            "keywords": {"type": "array", "items": {"type": "string"}, "description": "Custom keywords to search for"},
                            "days_back": {"type": "integer", "description": "Number of days to search", "default": 3}
                        },
                        "required": ["channels"]
                    }
                ),
                types.Tool(
                    name="send_standup_reminder",
                    description="Send a standup reminder or summary to a channel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string", "description": "Channel name or ID"},
                            "message": {"type": "string", "description": "Standup message or reminder text"},
                            "mention_users": {"type": "array", "items": {"type": "string"}, "description": "User IDs to mention"},
                            "thread_ts": {"type": "string", "description": "Thread timestamp to reply in thread"}
                        },
                        "required": ["channel", "message"]
                    }
                ),
                types.Tool(
                    name="get_user_activity",
                    description="Get user activity and engagement metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "Slack user ID"},
                            "channels": {"type": "array", "items": {"type": "string"}, "description": "Channels to analyze"},
                            "days_back": {"type": "integer", "description": "Number of days to analyze", "default": 14}
                        },
                        "required": ["user_id"]
                    }
                ),
                types.Tool(
                    name="create_poll",
                    description="Create a poll for team decisions or retrospective voting",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string", "description": "Channel name or ID"},
                            "question": {"type": "string", "description": "Poll question"},
                            "options": {"type": "array", "items": {"type": "string"}, "description": "Poll options"},
                            "anonymous": {"type": "boolean", "description": "Make poll anonymous", "default": False}
                        },
                        "required": ["channel", "question", "options"]
                    }
                ),
                types.Tool(
                    name="extract_action_items",
                    description="Extract action items and follow-ups from channel conversations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string", "description": "Channel name or ID"},
                            "days_back": {"type": "integer", "description": "Number of days to analyze", "default": 1},
                            "keywords": {"type": "array", "items": {"type": "string"}, "description": "Action item keywords", "default": ["todo", "action", "follow up", "will do", "should", "need to"]}
                        },
                        "required": ["channel"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            try:
                if name == "analyze_channel_sentiment":
                    result = await self._analyze_channel_sentiment(**arguments)
                elif name == "detect_team_blockers":
                    result = await self._detect_team_blockers(**arguments)
                elif name == "send_standup_reminder":
                    result = await self._send_standup_reminder(**arguments)
                elif name == "get_user_activity":
                    result = await self._get_user_activity(**arguments)
                elif name == "create_poll":
                    result = await self._create_poll(**arguments)
                elif name == "extract_action_items":
                    result = await self._extract_action_items(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_channel_id(self, channel: str) -> str:
        """Convert channel name to channel ID if needed"""
        if channel.startswith('C'):  # Already a channel ID
            return channel
        
        # Remove # if present
        channel_name = channel.lstrip('#')
        
        try:
            response = await self.client.conversations_list(types="public_channel,private_channel")
            for ch in response["channels"]:
                if ch["name"] == channel_name:
                    return ch["id"]
            
            raise ValueError(f"Channel '{channel}' not found")
        except SlackApiError as e:
            logger.error(f"Error finding channel {channel}: {e}")
            raise

    async def _get_messages(self, channel_id: str, days_back: int = 7, 
                           include_threads: bool = True) -> List[Dict]:
        """Get messages from a channel within the specified time range"""
        oldest = datetime.now() - timedelta(days=days_back)
        oldest_ts = str(int(oldest.timestamp()))
        
        messages = []
        cursor = None
        
        try:
            while True:
                params = {
                    "channel": channel_id,
                    "oldest": oldest_ts,
                    "limit": 100
                }
                if cursor:
                    params["cursor"] = cursor
                
                response = await self.client.conversations_history(**params)
                
                batch_messages = response["messages"]
                messages.extend(batch_messages)
                
                # Get thread replies if requested
                if include_threads:
                    for msg in batch_messages:
                        if msg.get("thread_ts") and msg["thread_ts"] == msg["ts"]:
                            # This is a parent message, get replies
                            try:
                                thread_response = await self.client.conversations_replies(
                                    channel=channel_id,
                                    ts=msg["ts"]
                                )
                                # Add replies (exclude the parent message)
                                replies = [r for r in thread_response["messages"] if r["ts"] != msg["ts"]]
                                messages.extend(replies)
                            except SlackApiError:
                                pass  # Continue if thread replies fail
                
                if not response.get("has_more"):
                    break
                    
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                    
        except SlackApiError as e:
            logger.error(f"Error fetching messages: {e}")
            raise
        
        return messages

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Simple sentiment analysis based on keywords and patterns"""
        positive_words = [
            'good', 'great', 'excellent', 'awesome', 'fantastic', 'love', 'perfect', 
            'amazing', 'wonderful', 'brilliant', 'outstanding', 'superb', 'thanks',
            'thank you', '👍', '🎉', '✅', '💚', '😊', '😃', '🙌'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'hate', 'horrible', 'frustrated', 'annoying',
            'difficult', 'problem', 'issue', 'bug', 'broken', 'stuck', 'blocked',
            'worried', 'concerned', '👎', '😞', '😢', '😤', '🚨', '❌'
        ]
        
        stress_indicators = [
            'overwhelmed', 'stressed', 'burnout', 'tired', 'exhausted', 'overwork',
            'too much', 'cant handle', "can't handle", 'struggling', 'pressure'
        ]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        stress_count = sum(1 for word in stress_indicators if word in text_lower)
        
        # Calculate sentiment score (-1 to +1)
        if positive_count == 0 and negative_count == 0:
            sentiment_score = 0
        else:
            sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
        
        # Determine sentiment category
        if sentiment_score > 0.3:
            sentiment = "positive"
        elif sentiment_score < -0.3:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "score": sentiment_score,
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "stress_indicators": stress_count
        }

    async def _analyze_channel_sentiment(self, channel: str, days_back: int = 7, 
                                       include_threads: bool = True) -> Dict[str, Any]:
        """Analyze sentiment and engagement patterns in a channel"""
        channel_id = await self._get_channel_id(channel)
        messages = await self._get_messages(channel_id, days_back, include_threads)
        
        if not messages:
            return {"error": "No messages found in the specified time period"}
        
        # Filter out bot messages and system messages
        human_messages = [
            msg for msg in messages 
            if msg.get("subtype") != "bot_message" and "text" in msg
        ]
        
        # Analyze each message
        sentiments = []
        user_activity = {}
        total_engagement = 0
        
        for msg in human_messages:
            text = msg["text"]
            user_id = msg.get("user", "unknown")
            
            # Skip if no actual text content
            if not text.strip():
                continue
            
            sentiment_analysis = self._analyze_sentiment(text)
            sentiments.append(sentiment_analysis)
            
            # Track user activity
            if user_id not in user_activity:
                user_activity[user_id] = {
                    "message_count": 0,
                    "sentiment_scores": [],
                    "stress_indicators": 0
                }
            
            user_activity[user_id]["message_count"] += 1
            user_activity[user_id]["sentiment_scores"].append(sentiment_analysis["score"])
            user_activity[user_id]["stress_indicators"] += sentiment_analysis["stress_indicators"]
            
            # Count engagement (reactions, replies)
            total_engagement += len(msg.get("reactions", []))
        
        # Calculate overall metrics
        if sentiments:
            avg_sentiment = sum(s["score"] for s in sentiments) / len(sentiments)
            positive_ratio = len([s for s in sentiments if s["sentiment"] == "positive"]) / len(sentiments)
            negative_ratio = len([s for s in sentiments if s["sentiment"] == "negative"]) / len(sentiments)
            total_stress_indicators = sum(s["stress_indicators"] for s in sentiments)
        else:
            avg_sentiment = 0
            positive_ratio = 0
            negative_ratio = 0
            total_stress_indicators = 0
        
        # Calculate user-level insights
        user_insights = {}
        for user_id, activity in user_activity.items():
            if activity["sentiment_scores"]:
                avg_user_sentiment = sum(activity["sentiment_scores"]) / len(activity["sentiment_scores"])
                user_insights[user_id] = {
                    "message_count": activity["message_count"],
                    "average_sentiment": avg_user_sentiment,
                    "stress_indicators": activity["stress_indicators"],
                    "engagement_level": "high" if activity["message_count"] > len(human_messages) / len(user_activity) else "normal"
                }
        
        return {
            "channel": channel,
            "analysis_period": f"{days_back} days",
            "total_messages": len(human_messages),
            "unique_users": len(user_activity),
            "overall_metrics": {
                "average_sentiment": avg_sentiment,
                "positive_ratio": positive_ratio,
                "negative_ratio": negative_ratio,
                "neutral_ratio": 1 - positive_ratio - negative_ratio,
                "total_engagement": total_engagement,
                "stress_indicators": total_stress_indicators
            },
            "user_insights": user_insights,
            "recommendations": self._get_sentiment_recommendations(avg_sentiment, total_stress_indicators, len(user_activity))
        }

    def _get_sentiment_recommendations(self, avg_sentiment: float, stress_indicators: int, 
                                     user_count: int) -> List[str]:
        """Generate recommendations based on sentiment analysis"""
        recommendations = []
        
        if avg_sentiment < -0.2:
            recommendations.append("Consider holding a team check-in to address concerns")
            recommendations.append("Review current workload and priorities")
        
        if stress_indicators > user_count * 2:  # More than 2 stress indicators per person on average
            recommendations.append("High stress levels detected - consider workload adjustment")
            recommendations.append("Schedule a retrospective to identify process improvements")
        
        if avg_sentiment > 0.3:
            recommendations.append("Team sentiment is positive - great job!")
            recommendations.append("Consider sharing this positive momentum with leadership")
        
        return recommendations

    async def _detect_team_blockers(self, channels: List[str], 
                                  keywords: Optional[List[str]] = None, 
                                  days_back: int = 3) -> Dict[str, Any]:
        """Detect mentions of blockers and impediments"""
        if not keywords:
            keywords = [
                "blocked", "blocker", "impediment", "stuck", "waiting for", "can't proceed",
                "dependency", "issue", "problem", "help needed", "escalation"
            ]
        
        all_blockers = []
        
        for channel in channels:
            try:
                channel_id = await self._get_channel_id(channel)
                messages = await self._get_messages(channel_id, days_back, include_threads=True)
                
                for msg in messages:
                    text = msg.get("text", "").lower()
                    
                    # Check for blocker keywords
                    found_keywords = [kw for kw in keywords if kw.lower() in text]
                    
                    if found_keywords:
                        user_info = await self._get_user_info(msg.get("user"))
                        
                        blocker = {
                            "channel": channel,
                            "user": user_info["name"] if user_info else "unknown",
                            "message": msg.get("text", ""),
                            "timestamp": datetime.fromtimestamp(float(msg["ts"])).isoformat(),
                            "keywords_found": found_keywords,
                            "urgency": self._assess_urgency(text),
                            "permalink": msg.get("permalink", "")
                        }
                        all_blockers.append(blocker)
                        
            except Exception as e:
                logger.error(f"Error analyzing channel {channel}: {e}")
                continue
        
        # Sort by urgency and timestamp
        all_blockers.sort(key=lambda x: (x["urgency"], x["timestamp"]), reverse=True)
        
        return {
            "blockers_found": len(all_blockers),
            "channels_analyzed": channels,
            "analysis_period": f"{days_back} days",
            "blockers": all_blockers,
            "summary": {
                "high_urgency": len([b for b in all_blockers if b["urgency"] == "high"]),
                "medium_urgency": len([b for b in all_blockers if b["urgency"] == "medium"]),
                "low_urgency": len([b for b in all_blockers if b["urgency"] == "low"])
            }
        }

    def _assess_urgency(self, text: str) -> str:
        """Assess urgency of a blocker based on text content"""
        high_urgency = ["urgent", "critical", "asap", "immediately", "emergency", "production"]
        medium_urgency = ["important", "soon", "today", "deadline"]
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in high_urgency):
            return "high"
        elif any(word in text_lower for word in medium_urgency):
            return "medium"
        else:
            return "low"

    async def _get_user_info(self, user_id: Optional[str]) -> Optional[Dict[str, str]]:
        """Get user information"""
        if not user_id:
            return None
            
        try:
            response = await self.client.users_info(user=user_id)
            user = response["user"]
            return {
                "id": user["id"],
                "name": user["name"],
                "real_name": user["profile"].get("real_name", user["name"])
            }
        except SlackApiError:
            return None

    async def _send_standup_reminder(self, channel: str, message: str, 
                                   mention_users: Optional[List[str]] = None,
                                   thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """Send a standup reminder or summary"""
        channel_id = await self._get_channel_id(channel)
        
        # Add user mentions if provided
        if mention_users:
            mentions = " ".join([f"<@{user_id}>" for user_id in mention_users])
            message = f"{mentions}\n\n{message}"
        
        try:
            params = {
                "channel": channel_id,
                "text": message
            }
            
            if thread_ts:
                params["thread_ts"] = thread_ts
            
            response = await self.client.chat_postMessage(**params)
            
            return {
                "success": True,
                "channel": channel,
                "message_ts": response["ts"],
                "permalink": response.get("permalink", "")
            }
            
        except SlackApiError as e:
            logger.error(f"Error sending message: {e}")
            return {"error": str(e)}

    async def _get_user_activity(self, user_id: str, channels: Optional[List[str]] = None, 
                               days_back: int = 14) -> Dict[str, Any]:
        """Get user activity metrics"""
        user_info = await self._get_user_info(user_id)
        if not user_info:
            return {"error": "User not found"}
        
        # If no channels specified, get user's channels
        if not channels:
            try:
                response = await self.client.conversations_list(types="public_channel,private_channel")
                channels = [ch["id"] for ch in response["channels"]]
            except SlackApiError as e:
                return {"error": f"Could not fetch channels: {e}"}
        
        total_messages = 0
        total_reactions_given = 0
        total_reactions_received = 0
        channels_active_in = 0
        sentiment_scores = []
        
        for channel in channels:
            try:
                if not channel.startswith('C'):
                    channel = await self._get_channel_id(channel)
                    
                messages = await self._get_messages(channel, days_back)
                
                user_messages = [msg for msg in messages if msg.get("user") == user_id]
                
                if user_messages:
                    channels_active_in += 1
                    total_messages += len(user_messages)
                    
                    # Analyze sentiment of user's messages
                    for msg in user_messages:
                        text = msg.get("text", "")
                        if text.strip():
                            sentiment = self._analyze_sentiment(text)
                            sentiment_scores.append(sentiment["score"])
                            
                        # Count reactions received
                        total_reactions_received += len(msg.get("reactions", []))
                
                # Count reactions given by this user
                for msg in messages:
                    for reaction in msg.get("reactions", []):
                        if user_id in reaction.get("users", []):
                            total_reactions_given += 1
                            
            except Exception as e:
                logger.error(f"Error analyzing user activity in channel {channel}: {e}")
                continue
        
        # Calculate averages
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        messages_per_day = total_messages / days_back
        
        return {
            "user": user_info,
            "analysis_period": f"{days_back} days",
            "activity_metrics": {
                "total_messages": total_messages,
                "messages_per_day": messages_per_day,
                "channels_active_in": channels_active_in,
                "reactions_given": total_reactions_given,
                "reactions_received": total_reactions_received,
                "average_sentiment": avg_sentiment
            },
            "engagement_level": self._assess_engagement_level(messages_per_day, total_reactions_given),
            "wellness_indicators": self._assess_wellness(avg_sentiment, messages_per_day)
        }

    def _assess_engagement_level(self, messages_per_day: float, reactions_given: int) -> str:
        """Assess user engagement level"""
        if messages_per_day > 10 or reactions_given > 20:
            return "high"
        elif messages_per_day > 2 or reactions_given > 5:
            return "normal"
        else:
            return "low"

    def _assess_wellness(self, avg_sentiment: float, messages_per_day: float) -> Dict[str, Any]:
        """Assess user wellness indicators"""
        indicators = []
        
        if avg_sentiment < -0.3:
            indicators.append("Negative sentiment trend detected")
        if messages_per_day < 1:
            indicators.append("Lower than normal activity")
        if messages_per_day > 20:
            indicators.append("Very high activity - possible overwork")
        
        wellness_score = "good"
        if len(indicators) > 0:
            wellness_score = "attention_needed" if len(indicators) == 1 else "concerning"
        
        return {
            "wellness_score": wellness_score,
            "indicators": indicators
        }

    async def _create_poll(self, channel: str, question: str, options: List[str], 
                         anonymous: bool = False) -> Dict[str, Any]:
        """Create a poll for team decisions"""
        channel_id = await self._get_channel_id(channel)
        
        # Build poll message
        poll_text = f"📊 **{question}**\n\n"
        
        # Add options with emoji reactions
        emoji_options = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, option in enumerate(options[:10]):  # Limit to 10 options
            poll_text += f"{emoji_options[i]} {option}\n"
        
        if anonymous:
            poll_text += "\n*This is an anonymous poll - react with the emoji that corresponds to your choice*"
        else:
            poll_text += "\n*React with the emoji that corresponds to your choice*"
        
        try:
            response = await self.client.chat_postMessage(
                channel=channel_id,
                text=poll_text
            )
            
            # Add reaction options to the message
            message_ts = response["ts"]
            for i in range(len(options)):
                await self.client.reactions_add(
                    channel=channel_id,
                    timestamp=message_ts,
                    name=emoji_options[i].encode('unicode_escape').decode('ascii').replace('\\U000', '').replace('\\u', '')
                )
            
            return {
                "success": True,
                "channel": channel,
                "question": question,
                "options": options,
                "message_ts": message_ts,
                "permalink": response.get("permalink", "")
            }
            
        except SlackApiError as e:
            logger.error(f"Error creating poll: {e}")
            return {"error": str(e)}

    async def _extract_action_items(self, channel: str, days_back: int = 1, 
                                  keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extract action items from channel conversations"""
        if not keywords:
            keywords = ["todo", "action", "follow up", "will do", "should", "need to"]
        
        channel_id = await self._get_channel_id(channel)
        messages = await self._get_messages(channel_id, days_back, include_threads=True)
        
        action_items = []
        
        for msg in messages:
            text = msg.get("text", "")
            if not text.strip():
                continue
            
            # Look for action item patterns
            sentences = text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if any(keyword in sentence.lower() for keyword in keywords):
                    # Extract potential assignee
                    assignee = None
                    if '<@' in sentence:
                        # Extract mentioned user
                        user_match = re.search(r'<@(\w+)>', sentence)
                        if user_match:
                            user_id = user_match.group(1)
                            user_info = await self._get_user_info(user_id)
                            assignee = user_info["name"] if user_info else user_id
                    
                    user_info = await self._get_user_info(msg.get("user"))
                    
                    action_item = {
                        "text": sentence,
                        "author": user_info["name"] if user_info else "unknown",
                        "assignee": assignee,
                        "timestamp": datetime.fromtimestamp(float(msg["ts"])).isoformat(),
                        "channel": channel,
                        "message_link": msg.get("permalink", "")
                    }
                    action_items.append(action_item)
        
        return {
            "action_items_found": len(action_items),
            "channel": channel,
            "analysis_period": f"{days_back} days",
            "action_items": action_items,
            "summary": {
                "total_items": len(action_items),
                "assigned_items": len([item for item in action_items if item["assignee"]]),
                "unassigned_items": len([item for item in action_items if not item["assignee"]])
            }
        }

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="slack-scrum-assistant",
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
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    
    if not bot_token:
        logger.error("Missing required environment variable: SLACK_BOT_TOKEN")
        return
    
    server = SlackMCPServer(bot_token, app_token)
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())