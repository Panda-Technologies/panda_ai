
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
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
from dotenv import load_dotenv
import os

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class AzureRagChat(KernelProcessStep[ConversationContext]):
    kernel: Kernel | None = None

    def __init__(self, load_env_vars=True):
        super().__init__()
        if load_env_vars:
            load_dotenv()

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

    def activate(self, state: KernelProcessStepState[ConversationContext]):
        self.state = state or ConversationContext()

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

        if self.kernel:
            self.chat_function = self.kernel.add_function(
                plugin_name="ChatBot",
                function_name="Chat",
                prompt_template_config=self.prompt_template_config
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

        # Prepare arguments for kernel invocation
        arguments = KernelArguments(
            chat_history=self.state.to_chat_history(),
            user_input=user_input,
            execution_settings=self.req_settings
        )

        # Generate response (non-streaming for now)
        response = await self.kernel.invoke(self.chat_function, arguments=arguments)

        self.state.add_user_message(user_input)
        self.state.add_assistant_message(str(response))

        return response