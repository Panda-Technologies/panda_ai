import logging
from typing import Dict, Any

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments, kernel_function
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext

class InformationRetrievalEvaluationStep(KernelProcessStep[ConversationContext]):
    kernel: Kernel | None = None
    state: ConversationContext | None = None

    def __init__(self):
        super().__init__()
        # logging.basicConfig(level=logging.INFO)

    async def activate(self, state: KernelProcessStepState[ConversationContext]):
        self._setup_information_retrieval()

    def _setup_information_retrieval(self):
        evaluation_template_config = PromptTemplateConfig(
            template="""You are a validation agent for an academic advising AI system. Your task is to determine when UNC-specific data lookups or Research-Augmented Generation (RAG) retrievals are needed.
            Core Validation Criteria:
            
            Only trigger lookups or retrievals when the latest user input explicitly requires it
            
            UNC-specific information (Return 'rag'):
            
            UNC major/degree requirements
            UNC course details and policies
            UNC department structure and advising
            UNC-specific offices, services, or locations
            Course equivalents at UNC for general requirements
            
            
            External information (Return 'web'):
            
            Requirements for external professional schools (medical, dental, pharmacy, law, etc.)
            National certification or licensing information
            Non-UNC academic programs or institutions
            General higher education trends or statistics
            Standardized test information (MCAT, LSAT, GRE, etc.)
            
            
            DO NOT assume that previous messages require a lookup
            
            Every query should be evaluated independently.
            If the user says 'ok thanks' or provides a generic response unrelated to a substantive question, do not initiate a lookup.
            
            
            Important distinction:
            
            When users ask about courses at UNC that would satisfy external requirements (like medical school prerequisites), return 'rag' as this requires UNC-specific course information.
            Only return 'web' when the query is exclusively about external requirements with no relation to UNC courses or programs.
            
            
            
            Example Responses
            
            "What are the CS major requirements at UNC?" → rag
            "What careers can I pursue with a Business degree?" → rag
            "What are the requirements for medical school admission?" → web
            "Give me the courses at UNC that could satisfy medical school requirements" → rag
            "What are the MCAT requirements?" → web
            
            Additional Safeguards:
            
            Never assume a persistent state from previous lookups. Every query is evaluated independently.
            Respond ONLY with 'rag' or 'web' based on the information needed.
            
            user_input = {{$user_input}}
            chat_history = {{$chat_history}}
            current_state = {{$current_state}}
            """,
            name="rag_evaluation",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="current_state", description="The current state", is_required=True),
            ]
        )
        if self.kernel:
            self.kernel.add_function(
                plugin_name="RagRecognizer",
                function_name="evaluate_rag_need",
                prompt_template_config=evaluation_template_config,
            )

    @kernel_function(name="analyze_rag_need")
    async def analyze_rag_need(self, context: KernelProcessStepContext, data: Dict[str, Any]):
        user_input = data.get("user_input", "")
        current_state = data.get("state", "")
        if self.kernel:
            response = await self.kernel.invoke(
                plugin_name="RagRecognizer",
                function_name="evaluate_rag_need",
                arguments=KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history(),
                    current_state=current_state,
                )
            )
        else:
            raise Exception("Kernel is not initialized")
        print(f"response: {response}")

        retrieval_type = str(response).strip().lower()
        data = {
            "retrieval_type": retrieval_type,
            "user_input": user_input,
        }

        await context.emit_event(process_event="RagEvaluated", data=data)
        return retrieval_type
