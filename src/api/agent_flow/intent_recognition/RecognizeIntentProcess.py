import json
import logging
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelArguments
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext

class IntentRecognitionStep(KernelProcessStep[ConversationContext]):
    kernel: Kernel | None = None
    state: ConversationContext | None = None

    def __init__(self):
        super().__init__()
        # logging.basicConfig(level=logging.INFO)

    async def activate(self, state: KernelProcessStepState[ConversationContext]):
        self._setup_intent_recognition()

    def _setup_intent_recognition(self):
        """Sets up the AI function for intent recognition."""
        intent_recognition_prompt = PromptTemplateConfig(
            template="""
            You are an AI assistant that analyzes user messages to determine their primary intent.
            Based on the following message and chat history to use as context (use chat history to 
            better determine if the current message is part of an overall flow or conversation intent)
            , identify the most likely intent from these categories:
            - initial: User is starting a new conversation or has just joined the chat. Look for keywords like "hello", "hi", "help", "start", etc.
            - degree_planning: User wants to discuss degree planning, academic paths, etc.
            - course_question: User wants help with class scheduling, course selection, enrollment, or mentions specific courses.
            - general_qa: General questions about the university, policies, asks about their personal information like their tasks, degree planners, 
              class schedules, etc. Anything tied to their account that must be retrieved. Also this can include questions about specific degree programs,
              as long as it does not pertain to degree planning. If a user asks the requirements for a specific degree, this is still general_qa.
              
            # IMPORTANT INFORMATION:
                - If the user is discussing anything assignment related, it is general_qa, and never course_question.
                  Course question only refers to course selection, scheduling, and enrollment.
                  
    
            User message: {{$user_input}}
            
            Chat history: {{$chat_history}}
    
            Respond ONLY in the following JSON format:
            {
                "intent": "one of the categories above",
                "confidence": a number between 0 and 1 representing your confidence
            }
            """,
            name="intent_recognition",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="chat_history", description="The chat history", is_required=True),
            ]
        )
        if self.kernel:
            self.kernel.add_function(
                plugin_name="IntentRecognizer",
                function_name="intent_recognition",
                prompt_template_config=intent_recognition_prompt,
            )

    @kernel_function(name="recognize_intent")
    async def recognize_intent(self, context: KernelProcessStepContext, user_input: str):
        """Recognizes the user's intent based on the input message and chat history."""
        if self.kernel:
            result = await self.kernel.invoke(
                plugin_name="IntentRecognizer",
                function_name="intent_recognition",
                arguments=KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history().messages,
                )
            )
        else:
            raise ValueError("Kernel is not initialized.")

        response_text = json.loads(str(result))

        match response_text["intent"]:
            case "initial":
                intent = "initial"
                confidence = response_text["confidence"]
            case "degree_planning":
                intent = "degree_planning"
                confidence = response_text["confidence"]
            case "course_question":
                intent = "course_question"
                confidence = response_text["confidence"]
            case "general_qa":
                intent = "general_qa"
                confidence = response_text["confidence"]
            case _:
                intent = "general_qa"
                confidence = 0.6

        data_result = {
            "intent": intent,
            "confidence": confidence,
            "user_input": user_input,
        }

        await context.emit_event(process_event="IntentRecognized", data=data_result)

        return data_result
