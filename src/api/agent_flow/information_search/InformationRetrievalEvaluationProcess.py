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
            
            Only trigger lookups or retrievals when the latest user input explicitly requests specific information that requires retrieval.
            
            ## Response Options
            ONLY respond with one of these three values:
            - 'rag' - For UNC-specific information lookup
            - 'web' - For external information lookup
            - 'none' - For no lookup needed (default for most interactions)
            
            ## When to Return 'rag' (UNC-specific information):
            
            #### **1. UNC Academic Information (Needs Data Lookup)**
            - Explicit requests for major/degree requirements (e.g., "What are the requirements for a Biology major?")
            - Specific course information queries (e.g., "Tell me about BIOL 101")
            - Department details (e.g., "What research areas does the Biology department focus on?")
            - Financial aid or administrative office info (e.g., "Where is the financial aid office located?")
            
            #### **2. Career Path & Planning (Needs RAG Retrieval)**
            - Explicit requests about career paths for a specific major (e.g., "What careers can I pursue with a Biology degree?")
            - Questions about professional pathways linked to a major (e.g., "What jobs can I get with a CS degree?")
            - Specific questions about industry trends for a major (e.g., "What's the job outlook for Biology graduates?")
            
            ## When to Return 'web' (External information):
            
            - Explicit requests about external professional schools (e.g., "What are medical school requirements?")
            - Questions about national certification or licensing (e.g., "How do I get certified as a Medical Lab Technician?")
            - Queries about non-UNC academic programs (e.g., "Which schools have the best Biology programs?")
            - Questions about standardized tests (e.g., "When should I take the MCAT?")
            
            ## When to Return 'none' (NO LOOKUP OR RAG NEEDED):
            
            #### **Basic Information Exchange**
            - Simple greetings like "hi", "hello", "thanks"
            - Basic preferences like "morning", "afternoon", "4 courses", "yes", "no"
            - Any numeric responses like "4", "5", etc.
            - Basic acknowledgments or single-word answers
            - Changing majors or degree types (e.g., "I want to do a biology bs instead")
            - Any statement of intention without specific information request
            
            #### **Exploration Phase**
            - "I like coding"
            - "I want to study psychology"
            - "I want a CS BS" → (Intent, not an academic info request)
            - "Business Administration bsba" → (Not enough context provided to initiate search)
            - Simple major declarations without specific requests for information
            - Any message that's simply providing basic information or preferences
            
            ## CRITICAL RULES
            
            1. NEVER return 'rag' or 'web' for simple responses like "morning", "afternoon", "4", "yes", "no"
            2. NEVER return 'rag' or 'web' for basic information collection (like preferences, numbers of courses, etc.)
            3. NEVER return 'rag' or 'web' when a user is merely changing their mind or switching majors
            4. ALWAYS default to 'none' unless there is an explicit question or request for specific information
            5. DO NOT assume that previous messages require a lookup
            6. DO NOT interpret a standalone career name as requiring 'rag' unless it's explicitly asking for career information
            7. When in doubt, return 'none'
            8. Statements of intention (e.g., "I want to do X") without specific questions DO NOT require lookups
            
            ## Example Responses
            
            "What are the CS major requirements at UNC?" → rag
            "What careers can I pursue with a Business degree?" → rag
            "What are the requirements for medical school admission?" → web
            "Give me the courses at UNC that could satisfy medical school requirements" → rag
            "What are the MCAT requirements?" → web
            "Computer science bs" → 'none'
            "I want to do a biology bs" → 'none'
            "I want to change to a psychology major" → 'none'
            "Morning" → 'none'
            "4" → 'none'
            "Yes" → 'none'
            "I am premed" → 'none' (unless specifically asking for premed information)
            "Software development" → 'none' (unless explicitly asking about career paths)
            "Data science and cybersecurity" → 'none' (unless explicitly asking about career paths)
            "Wait nevermind I want to do a biology bs" → 'none'
            
            ## Examples of 'none' responses (MOST COMMON):
            
            - "Hi" or "Hello"
            - "Thank you"
            - "Morning" or "Afternoon" or "Evening"
            - "4" or any other number
            - "Yes" or "No"
            - "What's the difference?"
            - "What do you mean?"
            - "Could you explain that?"
            - "I prefer morning classes"
            - "I'm interested in AI"
            - "Computer Science BS"
            - "Actually I'd prefer Biology instead"
            - "Nevermind, I want to pursue Biology BS"
            
            **IMPORTANT**
            - If the user's query is just stating a major name or changing majors, return 'none'
            - If the user's input is a simple response to a question, return 'none'
            - If the user is simply providing basic information about preferences or choices, ALWAYS return 'none'
            - If the user expresses a change of mind or intention without asking for specific information, return 'none'
            
            Remember: Respond ONLY with 'rag', 'web', or 'none' based on the information needed. DO NOT INCLUDE ANY EXPLANATION OR OTHER TEXT OR THE ''.
            
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
