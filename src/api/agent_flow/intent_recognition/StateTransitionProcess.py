from typing import Dict, Any

from semantic_kernel.functions import kernel_function
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext, ConversationState


class StateTransitionProcess(KernelProcessStep[ConversationContext]):
    state: ConversationContext | None = None

    async def activate(self, state: KernelProcessStepState[ConversationContext]):
        self.state = state.state or ConversationContext()

    @kernel_function(name="transition_state")
    async def transition_state(self, context: KernelProcessStepContext, intent_data: Dict[str, Any], user_input: str):
        """
        Transitions the conversation state based on the intent data and user input.
        """
        intent = intent_data.get("intent", "unknown")
        confidence = intent_data.get("confidence", 0.0)

        self.state.last_intent = intent

        if confidence < 0.6:
            # Stay in current state if confidence is low
            await context.emit_event(process_event="StateUnchanged", data={
                "state": self.state.artifact.current_state,
                "user_input": user_input
            })
            return

        # State transition logic
        if intent == "degree_planning" and self.state.artifact.current_state != ConversationState.DEGREE_PLANNING:
            self.state.artifact.current_state = ConversationState.DEGREE_PLANNING
            await context.emit_event(process_event="StateChanged", data={
                "state": ConversationState.DEGREE_PLANNING,
                "user_input": user_input
            })

        elif intent == "course_question" and self.state.artifact.current_state != ConversationState.COURSE_QUESTION:
            self.state.artifact.current_state = ConversationState.COURSE_QUESTION
            await context.emit_event(process_event="StateChanged", data={
                "state": ConversationState.COURSE_QUESTION,
                "user_input": user_input
            })

        elif intent == "general_qa" and self.state.artifact.current_state != ConversationState.GENERAL_QA:
            self.state.artifact.current_state = ConversationState.GENERAL_QA
            await context.emit_event(process_event="StateChanged", data={
                "state": ConversationState.GENERAL_QA,
                "user_input": user_input
            })
        else:
            # State didn't change, but we still need to pass along the user input
            await context.emit_event(process_event="StateUnchanged", data={
                "state": self.state.artifact.current_state,
                "user_input": user_input
            })




