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
            ### Core Validation Criteria:
            1. **Only trigger UNC Lookups or RAG Retrievals when the latest user input explicitly requires it**
               - **UNC data lookup is required for:**
                 - Major/degree requirements
                 - Course details and policies
                 - Department structure and advising
                 - UNC-specific offices, services, or locations
            
               - **RAG retrieval is required for:**
                 - Career goals in the context of a degree (e.g., 'I want to go into software engineering')
                 - Professional pathways linked to a major
                 - Industry trends for a specific major
            
            2. **DO NOT assume that previous messages require a lookup**
               - Every query should be evaluated independently.
               - If the user says 'ok thanks' or provides a generic response unrelated to a UNC or career question, return 'false' (no lookup needed).
            
            3. **Interest gathering phase (NO LOOKUP YET):**
               - If the user is exploring general interests (e.g., 'I like coding'), do **NOT** initiate a lookup.
               - A lookup or RAG retrieval should only be triggered once course requirements, career goals, or specific UNC-related questions are mentioned.
            
            4. **Distinguish degree requirements from career planning:**
               - 'What are the CS major requirements?' → true (UNC Data Lookup)
               - 'What careers can I pursue with a Business degree?' → true (RAG Retrieval)
               - 'I want a Computer Science BS' → false (Intent, not a request for lookup)
               - 'I'm interested in software engineering' → true (RAG Retrieval)
            
            ### **Validation Categories**
            #### **1. UNC Academic Information (Needs Data Lookup)**
            - Major/degree requirements
            - Course information
            - Department details
            - Financial aid or administrative office info
            
            #### **2. Career Path & Planning (Needs RAG Retrieval)**
            - Career goals in the context of a degree
            - Professional pathways linked to a major
            - Industry trends for a specific major
            - ANYTIME A USER SPECIFIES A SPECIFIC CAREER/CAREER GOAL
            
            ### **Example Responses**
            
            #### **Exploration Phase (NO LOOKUP OR RAG NEEDED)**
            - "I like coding" → **false**
            - "I want to study psychology" → **false**
            - "I want a CS BS" → **false** (Intent, not an academic info request)
            
            #### **Degree Matching & Specific Queries (LOOKUP NEEDED)**
            - "What are the CS major requirements?" → **true** (UNC Data Lookup)
            - "What courses do I need for a psychology degree?" → **true** (UNC Data Lookup)
            - "Tell me about the Biology degree" → **true** (UNC Data Lookup)
            
            #### **Career Interests (RAG RETRIEVAL NEEDED)**
            - "I want to go into software engineering" → **true** (RAG Retrieval)
            - "What jobs can I get with a CS degree?" → **true** (RAG Retrieval)
            - "I want to work in AI ethics" → **true** (RAG Retrieval)
            
            #### **General Academic & Non-UNC Queries (NO LOOKUP NEEDED)**
            - "What is computer science?" → **false**
            - "How do I choose a major?" → **false**
            - "Morning or evening classes?" → false
            - "How many courses should I take per semester?" → false
            
            ### Additional Safeguards:
            - **Never assume a persistent 'true' state from previous lookups.** Every query is evaluated independently.
            - **Differentiate between UNC-specific lookups and RAG-based career research.**
            - Respond **ONLY** with 'true' or 'false' based on whether a lookup is needed. Do not include ** in your response.
            
            user_input = {{$user_input}}
            
            chat_history = {{$chat_history}}
            
            current_state = {{$current_state}}
            
            ---
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

        needs_rag = str(response).strip().lower() == "true"
        data = {
            "needs_rag": needs_rag,
            "user_input": user_input,
        }

        await context.emit_event(process_event="RagEvaluated", data=data)
        return needs_rag
