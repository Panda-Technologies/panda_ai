from typing import Dict, Any

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelArguments
from semantic_kernel.processes.kernel_process import KernelProcessStep, KernelProcessStepState, KernelProcessStepContext

from src.api.agent_flow.ProcessValidation.DegreePlanningStageValidation import DegreePlanningStageValidation
from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext
from src.api.agent_flow.response_creation.ResponseGenerator import ResponseGenerator


class ResponseStep(KernelProcessStep[ConversationContext]):
    kernel: Kernel | None = None
    state: ConversationContext = None
    response_generator: ResponseGenerator = None
    degree_plan_validator: DegreePlanningStageValidation = None

    def __init__(self):
        super().__init__()

    async def activate(self, state: KernelProcessStepState[ConversationContext]):
        self.response_generator = ResponseGenerator(self.kernel, self.state)
        self.degree_plan_validator = DegreePlanningStageValidation(kernel=self.kernel, state=self.state)

    def _check_data_completeness(self):
        if self.state.artifact.current_state == "degree_planning":
            required_fields = {
                "major": self.state.artifact.major,
                "degree_type": self.state.artifact.degree_type,
                "current_term": self.state.artifact.current_term is not None,
                "start_term": self.state.artifact.start_term is not None,
                "preferred_courses_per_semester": self.state.artifact.preferred_courses_per_semester is not None,
                "career_goals": self.state.artifact.career_goals and len(self.state.artifact.career_goals) > 0
            }
        else:  # course scheduling state
            required_fields = {
                "major": self.state.artifact.major,
                "current_term": self.state.artifact.current_term is not None,
                "time_preference": self.state.artifact.time_preference is not None,
                "preferred_courses_per_semester": self.state.artifact.preferred_courses_per_semester is not None
            }

        missing = [field for field, value in required_fields.items() if not value]
        total = len(required_fields)
        complete = total - len(missing)

        return {
            "percentage": round((complete / total) * 100),
            "missing": missing,
            "is_complete": len(missing) == 0
        }

    @kernel_function(name="generate_response")
    async def generate_response(self, context: KernelProcessStepContext, data: Dict[str, Any]) -> str:
        user_input: str = data.get("user_input", "No user input provided. Please provide user input.")
        retrieval_type: str = data.get("retrieval_type", "none")
        arguments: KernelArguments
        data_completeness = self._check_data_completeness()
        missing_fields = data_completeness.get("missing", [])
        degree_plan_step: str | None = None

        match self.state.artifact.current_state:
            case "initial":
                arguments = KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history().messages,
                )
            case "degree_planning":
                degree_plan_step = await self.degree_plan_validator.determine_degree_planning_state(user_input, missing_fields)
                arguments = KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history().messages,
                )
            case "course_question":
                arguments = KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history().messages,
                    missing_fields=missing_fields,
                )
            case "general_qa":
                arguments = KernelArguments(
                    user_input=user_input,
                    chat_history=self.state.to_chat_history().messages,
                )
            case _:
                raise ValueError(f"Invalid state: {self.state.artifact.current_state}")

        response = await self.response_generator.generate_response(user_input=user_input, arguments=arguments,
                                                                   retrieval_type=retrieval_type, state=self.state, degree_plan_step=degree_plan_step)

        response_text = str(response)

        self.state.add_user_message(user_input)
        self.state.add_assistant_message(response_text)

        print(f"state: {self.state.artifact.current_state}")
        print(f"chat_history: {self.state.to_chat_history().messages}")
        return response_text
