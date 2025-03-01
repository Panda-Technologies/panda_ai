
import logging
from pydantic import SecretStr

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureAISearchDataSource,
    AzureChatCompletion,
    AzureChatPromptExecutionSettings,
    ExtraBody,
)
from semantic_kernel.connectors.memory.azure_cognitive_search.azure_ai_search_settings import AzureAISearchSettings
from semantic_kernel.contents import ChatHistory, ChatMessageContent
from semantic_kernel.functions import KernelArguments, FunctionResult
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
from dotenv import load_dotenv
import os


class AzureRagChat:
    def __init__(self, load_env_vars=True):
        if load_env_vars:
            load_dotenv()

        self.kernel = Kernel()
        logging.basicConfig(level=logging.INFO)

        # Initialize Azure OpenAI service
        self.chat_service = AzureChatCompletion(
            service_id="chat-gpt",
            deployment_name=os.environ.get("AZURE_DEPLOYMENT_NAME"),
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview"
        )
        self.kernel.add_service(self.chat_service)

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

        # Set up the chat function
        self._setup_chat_function()

    def _setup_chat_function(self):
        """Set up the chat function with the correct prompt template."""
        self.prompt_template_config = PromptTemplateConfig(
            template="{{$chat_history}}\nUser: {{$user_input}}\nAssistant:",
            name="chat",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="user_input", description="The user input", is_required=True),
            ],
            execution_settings={"default": self.req_settings},
        )

        self.chat_function = self.kernel.add_function(
            plugin_name="ChatBot",
            function_name="Chat",
            prompt_template_config=self.prompt_template_config
        )

    async def generate_response(
            self,
            user_input: str,
            chat_history: ChatHistory = None,
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
        # Create a new chat history if none is provided
        if chat_history is None:
            chat_history = ChatHistory()
            chat_history.add_system_message(
                "I am an AI assistant here to answer your UNC Chapel Hill university questions."
            )
        # Convert string to ChatHistory if needed
        elif isinstance(chat_history, str):
            temp_history = ChatHistory()
            temp_history.add_system_message(chat_history)
            chat_history = temp_history

        # Prepare arguments for kernel invocation
        arguments = KernelArguments(
            chat_history=chat_history,
            user_input=user_input,
            execution_settings=self.req_settings
        )

        # Generate response (non-streaming for now)
        response = await self.kernel.invoke(self.chat_function, arguments=arguments)

        return response