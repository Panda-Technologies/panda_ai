from pydantic import SecretStr
import os
from typing import Optional, Union

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureAISearchDataSource,
    AzureChatPromptExecutionSettings,
    ExtraBody,
)
from semantic_kernel.connectors.memory.azure_cognitive_search.azure_ai_search_settings import AzureAISearchSettings
from semantic_kernel.connectors.search.bing import BingSearch
from semantic_kernel.functions import KernelArguments, KernelPlugin, FunctionResult, KernelParameterMetadata
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.contents import ChatHistory
from dotenv import load_dotenv

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class AzureRagChat:
    """Class that supports both RAG-based chat and web search-based chat."""

    def __init__(
            self,
            state: ConversationContext,
            retrieval_type: str,
            kernel: Kernel,
            prompt_template: PromptTemplateConfig,
            query: str,
            chat_history: Optional[Union[ChatHistory, str]] = None,
            load_env_vars: bool = True
    ):
        """Initialize the RAG chat system.

        Args:
            state: The conversation context
            retrieval_type: Either "rag" or "web" to determine the retrieval method
            kernel: The Semantic Kernel instance to use
            prompt_template: The prompt template to use for generating responses
            query: The user's query
            chat_history: Optional chat history
            load_env_vars: Whether to load environment variables
        """
        self.state = state
        self.kernel = kernel
        if load_env_vars:
            load_dotenv()

        self.retrieval_type = retrieval_type.lower()
        if self.retrieval_type not in ["rag", "web"]:
            raise ValueError("retrieval_type must be either 'rag' or 'web'")

        self.prompt_template = prompt_template
        self.query = query
        self.chat_history = chat_history

        # Configure the appropriate retrieval method
        if self.retrieval_type == "rag":
            self._setup_rag_retrieval()
        else:  # web
            self._setup_web_retrieval()

        # Set up the chat function
        self._setup_chat_function()

    def _setup_rag_retrieval(self):
        """Set up RAG retrieval using Azure AI Search."""
        # Initialize Azure AI Search settings
        self.azure_ai_search_settings = AzureAISearchSettings(
            endpoint=os.environ.get("AZURE_AISEARCH_ENDPOINT"),
            index_name=os.environ.get("AZURE_AISEARCH_INDEX_NAME"),
            api_key=SecretStr(os.environ.get("AZURE_AISEARCH_KEY")),
        )

        # Set up RAG data source
        self.az_source = AzureAISearchDataSource.from_azure_ai_search_settings(
            azure_ai_search_settings=self.azure_ai_search_settings
        )
        self.extra_body = ExtraBody(data_sources=[self.az_source])
        self.req_settings = AzureChatPromptExecutionSettings(service_id="default", extra_body=self.extra_body)

    def _setup_web_retrieval(self):
        """Set up web retrieval using Bing Search."""
        # Create a Bing Search connector
        bing_search = BingSearch(
            api_key=os.environ.get("BING_SEARCH_KEY")
        )

        # Add Bing search as a plugin to the kernel
        self.kernel.add_plugin(
            KernelPlugin.from_text_search_with_search(
                bing_search,
                plugin_name="bing",
                description="Search the web for information.",
                parameters=[
                    KernelParameterMetadata(
                        name="query",
                        description="The search query.",
                        type="str",
                        is_required=True,
                        type_object=str,
                    ),
                    KernelParameterMetadata(
                        name="top",
                        description="The number of results to return.",
                        type="int",
                        is_required=False,
                        default_value=3,
                        type_object=int,
                    ),
                    KernelParameterMetadata(
                        name="site",
                        description="Filter results to a specific site.",
                        type="str",
                        is_required=False,
                        type_object=str,
                    ),
                ],
            )
        )

        # Create execution settings without extra_body for web search
        self.req_settings = AzureChatPromptExecutionSettings(service_id="default")

    def _setup_chat_function(self):
        """Set up the chat function with the correct prompt template."""
        self.prompt_template_config = self.prompt_template
        self.prompt_template_config.add_execution_settings(self.req_settings)

        self.chat_function = self.kernel.add_function(
            plugin_name="ChatBot",
            function_name="Chat",
            prompt_template_config=self.prompt_template_config,
        )

    async def generate_response(self) -> FunctionResult:
        """Generate a response to the user input using the provided chat history.

        Returns:
            FunctionResult containing the response
        """
        args = KernelArguments(query=self.query)

        # Generate response
        response = await self.kernel.invoke(self.chat_function, arguments=args)
        return response