import logging

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments, kernel_function
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext

class InformationRetrievalEvaluationStep(KernelProcessStep[ConversationContext]):
    kernel: Kernel | None = None

    def __init__(self):
        super().__init__()
        logging.basicConfig(level=logging.INFO)

    async def activate(self, state: KernelProcessStepState[ConversationContext]):
        self.state = state.state or ConversationContext()
        self._setup_information_retrieval()

    def _setup_information_retrieval(self):
        evaluation_template_config = PromptTemplateConfig(
            template="""Evaluate if the following user query requires accessing external knowledge or if it can be 
            answered using general knowledge. Respond with either 'true' or 'false'. You must always answer with 'true' 
            when a specific degree or class is mentioned by name such as "computer science, biology, chemistry, etc." 
            However, do not answer with 'true' if the user requests to just plan a degree. Also, use the chat history as
            context to determine if the user query requires external knowledge. However, ensure you are not just looking at the
            chat history to determine if external knowledge is needed, but rather the context of the chat history in relation to the user query.


            User query: {{$user_input}}

            Chat history: {{$chat_history}}

            Consider:
            1. Does this require specific factual information?
            2. Does this ask about particular documents or data?
            3. Is this something that requires current or historical context?
            4. Is this mentioning or discussing a specific degree or class? If so, then it likely requires external knowledge.
            5. Anything UNC related should be marked as 'true'.
            6. If the user is asking for any financial aid or scholarships information, it should be marked as 'true'.
            """,
            name="rag_evaluation",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="chat_history", description="The chat history", is_required=True),
            ]
        )
        if self.kernel:
            self.kernel.add_function(
                plugin_name="RagRecognizer",
                function_name="evaluate_rag_need",
                prompt_template_config=evaluation_template_config,
            )

    @kernel_function(name="analyze_rag_need")
    async def analyze_rag_need(self, context: KernelProcessStepContext, user_input: str):
        if self.kernel:
            response = await self.kernel.invoke(
                plugin_name="RagRecognizer",
                function_name="evaluate_rag_need",
                arguments=KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history(),
                )
            )
        else:
            response = "No kernel found"

        needs_rag = str(response).strip().lower() == "true"
        print(f"needs rag {needs_rag}")

        await context.emit_event(process_event="RagEvaluated", data={"needs_rag": needs_rag})
        return needs_rag
