"""
SM-Assistant Azure AI Foundry Agent Template
Integrates our working Azure AI Foundry agent calls with Semantic Kernel orchestration
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from v3.magentic_agents.common.lifecycle import AzureAgentBase
from v3.magentic_agents.models.agent_models import MCPConfig

import os
import dotenv

# Load environment
dotenv.load_dotenv()


class SMFoundryAgent(AzureAgentBase):
    """
    SM-Assistant Azure AI Foundry Agent that integrates with Semantic Kernel
    Uses our working Azure AI Foundry API calls within SK orchestration framework
    """

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        agent_instructions: str,
        model_deployment_name: str,
        capability_type: str,
        mcp_config: MCPConfig | None = None,
    ) -> None:
        super().__init__(mcp=mcp_config)
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.agent_instructions = agent_instructions
        self.model_deployment_name = model_deployment_name
        self.capability_type = capability_type  # BacklogIntelligence, MeetingIntelligence, etc.
        self.mcp = mcp_config
        self.logger = logging.getLogger(__name__)
        
        # Azure AI Foundry client (using our working pattern)
        self._ai_client: Optional[AIProjectClient] = None
        self._foundry_agent_id: Optional[str] = None
        
        # SK Agent wrapper
        self._agent: Optional[Agent] = None

    async def _get_ai_client(self) -> AIProjectClient:
        """Get authenticated Azure AI Project client (same pattern as main_simple_foundry.py)"""
        if self._ai_client is None:
            try:
                credential = DefaultAzureCredential()
                
                self._ai_client = AIProjectClient(
                    endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or "https://default-endpoint",
                    credential=credential
                )
                
                self.logger.info(f"✅ Azure AI Project client initialized for {self.agent_name}")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Azure AI Project client: {e}")
                raise
        
        return self._ai_client

    async def _find_sm_foundry_agent(self) -> Optional[Any]:
        """Find the corresponding SM-Asst agent in Azure AI Foundry"""
        try:
            client = await self._get_ai_client()
            all_agents = client.agents.list_agents()
            
            # Look for SM-Asst agent that matches our capability
            async for agent in all_agents:
                if (agent.name and 
                    "SM-Asst" in agent.name and 
                    self.capability_type in agent.name):
                    self.logger.info(f"✅ Found Azure AI Foundry agent: {agent.name}")
                    return agent
            
            # If no exact match, find any SM-Asst agent
            all_agents = client.agents.list_agents()
            async for agent in all_agents:
                if agent.name and "SM-Asst" in agent.name:
                    self.logger.info(f"⚠️ Using fallback SM-Asst agent: {agent.name}")
                    return agent
                    
            self.logger.warning(f"❌ No SM-Asst agent found for {self.capability_type}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding Azure AI Foundry agent: {e}")
            return None

    async def _after_open(self) -> None:
        """Initialize the agent - find the Azure AI Foundry agent and set up SK wrapper"""
        try:
            # Find the corresponding Azure AI Foundry agent
            foundry_agent = await self._find_sm_foundry_agent()
            if foundry_agent:
                self._foundry_agent_id = foundry_agent.id
                self.logger.info(f"🔗 Linked to Azure AI Foundry agent: {foundry_agent.name}")
            else:
                raise Exception(f"Could not find Azure AI Foundry agent for {self.capability_type}")
            
            # Create a simple SK Agent wrapper that delegates to Azure AI Foundry
            self._agent = SKFoundryAgentWrapper(
                name=self.agent_name,
                description=self.agent_description,
                instructions=self.agent_instructions,
                foundry_client=await self._get_ai_client(),
                foundry_agent_id=self._foundry_agent_id,
                logger=self.logger
            )
            
            self.logger.info(f"✅ SM-Assistant {self.capability_type} agent initialized with SK integration")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize SM-Assistant agent: {e}")
            raise

    @property
    def agent(self) -> Agent:
        """Return the SK Agent for orchestration"""
        if self._agent is None:
            raise RuntimeError("Agent not initialized - call open() first")
        return self._agent

    @property 
    def id(self) -> str:
        """Agent ID for SK orchestration"""
        return self.agent_name

    @property
    def name(self) -> str:
        """Agent name for SK orchestration"""
        return self.agent_name

    async def close(self) -> None:
        """Clean up resources"""
        try:
            if self._ai_client:
                await self._ai_client.close()
                self.logger.info(f"🧹 Closed Azure AI client for {self.agent_name}")
        except Exception as e:
            self.logger.warning(f"⚠️ Error closing {self.agent_name}: {e}")

    async def invoke(self, message: str) -> str:
        """Direct invocation method for testing"""
        if not self._agent:
            raise RuntimeError("Agent not initialized")
        
        # Create a chat message and invoke the agent
        chat_message = ChatMessageContent(
            role=AuthorRole.USER,
            content=message
        )
        
        # Use the SK agent wrapper to process the message
        response = await self._agent.invoke([chat_message])
        return str(response)


class SKFoundryAgentWrapper(Agent):
    """
    Semantic Kernel Agent wrapper that delegates to Azure AI Foundry
    This makes our Azure AI Foundry agents compatible with SK orchestration
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        instructions: str,
        foundry_client: AIProjectClient,
        foundry_agent_id: str,
        logger: logging.Logger
    ):
        super().__init__(
            name=name,
            description=description,
            instructions=instructions
        )
        self.foundry_client = foundry_client
        self.foundry_agent_id = foundry_agent_id
        self.logger = logger

    async def invoke(self, messages: List[ChatMessageContent]) -> ChatMessageContent:
        """
        Invoke the Azure AI Foundry agent using our working API pattern
        This is called by SK orchestration
        """
        try:
            # Get the latest user message
            user_message = None
            for msg in reversed(messages):
                if msg.role == AuthorRole.USER:
                    user_message = str(msg.content)
                    break
            
            if not user_message:
                user_message = "Hello"
            
            self.logger.info(f"🎯 {self.name} processing: {user_message}")
            
            # Use our working Azure AI Foundry pattern (from main_simple_foundry.py)
            thread = await self.foundry_client.agents.threads.create()
            
            await self.foundry_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_message
            )
            
            run = await self.foundry_client.agents.runs.create(
                thread_id=thread.id,
                agent_id=self.foundry_agent_id
            )
            
            # Poll for completion
            max_attempts = 30
            attempt = 0
            while run.status in ["queued", "in_progress"] and attempt < max_attempts:
                await asyncio.sleep(2)
                run = await self.foundry_client.agents.runs.get(
                    thread_id=thread.id, 
                    run_id=run.id
                )
                attempt += 1
            
            if run.status == "completed":
                # Get the response
                messages_response = self.foundry_client.agents.messages.list(thread_id=thread.id)
                assistant_messages = []
                async for msg in messages_response:
                    if msg.role == "assistant":
                        assistant_messages.append(msg)
                
                if assistant_messages:
                    response_content = assistant_messages[0].content[0].text.value
                    self.logger.info(f"✅ {self.name} responded: {response_content[:100]}...")
                    
                    return ChatMessageContent(
                        role=AuthorRole.ASSISTANT,
                        content=response_content,
                        name=self.name
                    )
            
            # Handle failed runs
            error_msg = f"Agent run failed with status: {run.status}"
            self.logger.error(f"❌ {self.name}: {error_msg}")
            
            return ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=f"I apologize, but I encountered an error: {error_msg}",
                name=self.name
            )
            
        except Exception as e:
            error_msg = f"Error invoking {self.name}: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=f"I apologize, but I encountered an error: {str(e)}",
                name=self.name
            )