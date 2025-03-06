
import logging
from pydantic import SecretStr

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import FunctionChoiceBehavior, PromptExecutionSettings
from semantic_kernel.connectors.ai.open_ai import (
    AzureAISearchDataSource,
    AzureChatPromptExecutionSettings,
    ExtraBody,
)
from semantic_kernel.connectors.memory.azure_cognitive_search.azure_ai_search_settings import AzureAISearchSettings
from semantic_kernel.functions import KernelArguments, FunctionResult
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
from dotenv import load_dotenv
import os

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class AzureRagChat:

    def __init__(self, state: ConversationContext, kernel: Kernel, prompt_template: PromptTemplateConfig, query: str, load_env_vars=True):
        self.state = state
        self.kernel = kernel
        if load_env_vars:
            load_dotenv()

        # Initialize Azure AI Search settings
        self.azure_ai_search_settings = AzureAISearchSettings(
            endpoint=os.environ.get("AZURE_AISEARCH_ENDPOINT"),
            index_name=os.environ.get("AZURE_AISEARCH_INDEX_NAME"),
            api_key=SecretStr(os.environ.get("AZURE_AISEARCH_KEY")),
        )

        self.prompt_template = prompt_template
        self.query = query

        # Set up RAG data source
        self.az_source = AzureAISearchDataSource.from_azure_ai_search_settings(
            azure_ai_search_settings=self.azure_ai_search_settings
        )
        self.extra_body = ExtraBody(data_sources=[self.az_source])
        self.req_settings = AzureChatPromptExecutionSettings(service_id="default", extra_body=self.extra_body)

        self._setup_chat_function()

    def _setup_chat_function(self):
        """Set up the chat function with the correct prompt template."""
        self.prompt_template_config = self.prompt_template
        self.prompt_template_config.add_execution_settings(self.req_settings)

        self.chat_function = self.kernel.add_function(
            plugin_name="ChatBot",
            function_name="Chat",
            prompt_template_config=self.prompt_template_config,
        )

    async def generate_response(
            self,
            user_input: str,
            streaming: bool = False
    ) -> FunctionResult:
        """Generate a response to the user input using the provided chat history.

        Args:
            user_input: The user's message
            chat_history: Optional chat history (either ChatHistory object or string)
            streaming: Whether to stream the response (not implemented yet)

        Returns:
            Tuple of (response text, updated chat history)
        """

        # Generate response (non-streaming for now)
        response = await self.kernel.invoke(self.chat_function, arguments=KernelArguments(query=self.query))
        return response