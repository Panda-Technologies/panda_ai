import json
from typing import Dict, Any

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelArguments
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.ProcessValidation.DegreePlanningValidationPrompt import degree_planning_validation_prompt
from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class DegreePlanningValidationStep(KernelProcessStep[ConversationContext]):
    state: ConversationContext | None = None
    kernel: Kernel | None = None

    def __init__(self):
        super().__init__()

    async def activate(self, step: KernelProcessStepState[ConversationContext]):
        self._setup_validation_functions()

    def _setup_validation_functions(self):
        extraction_prompt_config = PromptTemplateConfig(
            template=degree_planning_validation_prompt,
            input_variables=[
                InputVariable(name="chat_history", description="The chat history to extract information from",
                              is_required=True),
            ],
            template_format="semantic-kernel",
            name="conversation_artifact_extractor",
            description="Extracts a conversation artifact from chat history"
        )
        self.kernel.add_function(
            prompt_template_config=extraction_prompt_config,
            plugin_name="DegreePlanningValidation",
            function_name="validate_degree_planning",
        )

    @kernel_function(name="validate_degree_planning")
    async def validate_degree_planning(self, context: KernelProcessStepContext, data: Dict[str, Any]) -> str:
        """
        Validates if the user's input is related to degree planning.
        """
        if self.kernel:
            validated_degree_planning = await self.kernel.invoke(
                plugin_name="DegreePlanningValidation",
                function_name="validate_degree_planning",
                arguments=KernelArguments(
                    chat_history=self.state.to_chat_history().messages
                )
            )
        else:
            raise ValueError("Kernel is not initialized.")

        validated_state = json.loads(str(validated_degree_planning))

        # Get current state from artifact
        current_state = self.state.artifact.current_state

        # Check if validated state differs from current state
        if validated_state["current_state"] != current_state:
        # Update state in artifact
            self.state.artifact.current_state = validated_state["current_state"]

        # Update other relevant fields from validated state
        if validated_state["degree_type"]:
            self.state.artifact.degree_type = validated_state["degree_type"]

        if validated_state["major"]:
            self.state.artifact.major = validated_state["major"]

        if validated_state["time_preference"]:
            self.state.artifact.time_preference = validated_state["time_preference"]

        if validated_state["current_term"]:
            self.state.artifact.current_term = validated_state["current_term"]

        if validated_state["preferred_courses_per_semester"]:
            self.state.artifact.preferred_courses_per_semester = validated_state["preferred_courses_per_semester"]

        if validated_state["career_goals"]:
            self.state.artifact.career_goals = validated_state["career_goals"]

        if validated_state["courses_selected"]:
            for course in validated_state["courses_selected"]:
                if course not in self.state.artifact.courses_selected:
                    self.state.artifact.courses_selected.append(course)
        await context.emit_event(process_event="DegreePlanningValidationStateChanged", data=data)
        return f"State changed from {current_state} to {validated_state['current_state']}"


