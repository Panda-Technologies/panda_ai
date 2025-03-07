import logging
from typing import Dict, Any

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class StateTransitionProcess(KernelProcessStep[ConversationContext]):
    kernel: Kernel | None = None
    state: ConversationContext | None = None

    def __init__(self):
        super().__init__()
        # logging.basicConfig(level=logging.INFO)

    async def activate(self, state: KernelProcessStepState[ConversationContext]):
        print(f"StateTransitionProcess")

    @kernel_function(name="transition_state")
    async def transition_state(self, context: KernelProcessStepContext, data: Dict[str, Any]):
        """
        Transitions the conversation state based on the intent data and user input.
        """
        intent = data.get("intent", "unknown")
        confidence = data.get("confidence", 0.0)
        user_input = data.get("user_input", "No user input provided. Abort transition.")

        self.state.last_intent = intent

        if confidence < 0.7:
            # Stay in current state if confidence is low
            await context.emit_event(process_event="StateUnchanged", data={
                "state": self.state.artifact.current_state,
                "user_input": user_input
            })
            return

        # State transition logic
        if intent == "degree_planning" and self.state.artifact.current_state != "degree_planning":
            self.state.artifact.current_state = "degree_planning"
            await context.emit_event(process_event="StateChanged", data={
                "state": "degree_planning",
                "user_input": user_input
            })

        elif intent == "course_question" and self.state.artifact.current_state != "course_question":
            self.state.artifact.current_state = "course_question"
            await context.emit_event(process_event="StateChanged", data={
                "state": "course_question",
                "user_input": user_input
            })

        elif intent == "general_qa" and self.state.artifact.current_state != "general_qa":
            self.state.artifact.current_state = "general_qa"
            await context.emit_event(process_event="StateChanged", data={
                "state": "general_qa",
                "user_input": user_input
            })
        else:
            # State didn't change, but we still need to pass along the user input
            await context.emit_event(process_event="StateUnchanged", data={
                "state": self.state.artifact.current_state,
                "user_input": user_input
            })




