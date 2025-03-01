from typing import Dict, Any

from pydantic import SecretStr
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.memory.azure_cognitive_search.azure_ai_search_settings import AzureAISearchSettings
from semantic_kernel.processes import ProcessBuilder

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext
from src.api.agent_flow.chat_flow.ResponseGenerator import ResponseGenerator
from src.api.agent_flow.information_search.InformationRetrievalEvaluationProcess import \
    InformationRetrievalEvaluationStep


class ConversationStateManager:
    def __init__(self,
                 azure_openai_deployment: str,
                 azure_openai_endpoint: str,
                 azure_openai_api_key: str,
                 azure_search_endpoint: str,
                 azure_search_api_key: str,
                 azure_search_index: str, service_id: str = "default"):
        self.chat_service = AzureChatCompletion(
            deployment_name=azure_openai_deployment,
            endpoint=azure_openai_endpoint,
            api_key=azure_openai_api_key,
            api_version="2024-02-15-preview"
        )
        self.kernel = Kernel()
        self.kernel.add_service(self.chat_service)
        self.azure_ai_search_settings = AzureAISearchSettings(
            endpoint=azure_search_endpoint,
            index_name=azure_search_index,
            api_key=SecretStr(azure_search_api_key),
        )
        self.response_generator = ResponseGenerator(self.kernel)
        self.process_builder = self._build_process()
        self.process = self.process_builder.build()
        self.context = ConversationContext()


    def _build_process(self) -> ProcessBuilder:
        process = ProcessBuilder(name="ConversationStateManager")

        def create_rag_step():
            step = InformationRetrievalEvaluationStep()
            step.kernel = self.kernel
            return step

        rag_evaluation_step = process.add_step(
            InformationRetrievalEvaluationStep,
            factory_function=create_rag_step,
        )

        process.on_input_event(event_id="UserInput").send_event_to(
            rag_evaluation_step,
            parameter_name="user_input"
        )

        return process

    async def process_message(self, user_input: str):
        from semantic_kernel.processes.local_runtime.local_kernel_process import start
        from semantic_kernel.processes.kernel_process.kernel_process_event import KernelProcessEvent

        event_data = user_input

        result = await start(
            process=self.process,
            kernel=self.kernel,
            initial_event=KernelProcessEvent(id="UserInput", data=event_data)
        )