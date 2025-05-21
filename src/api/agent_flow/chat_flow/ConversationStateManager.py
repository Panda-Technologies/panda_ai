from typing import TypeVar, Type

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.processes import ProcessBuilder

from src.api.agent_flow.ProcessValidation.DegreePlanningValidationStep import DegreePlanningValidationStep
from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext
from src.api.agent_flow.intent_recognition.StateTransitionProcess import StateTransitionProcess
from src.api.agent_flow.response_creation.ResponseGenerator import ResponseGenerator
from src.api.agent_flow.information_search.InformationRetrievalEvaluationProcess import \
    InformationRetrievalEvaluationStep
from src.api.agent_flow.intent_recognition.RecognizeIntentProcess import IntentRecognitionStep
from src.api.agent_flow.response_creation.ResponseProcessStep import ResponseStep
from src.api.agent_plugins.Course import CourseRecommendationPlugin
from src.api.agent_plugins.DegreeInfo import DegreeInfoPlugin
from src.api.agent_plugins.StudentInfo import StudentInfoPlugin


class ConversationStateManager:
    def __init__(self,
                 azure_openai_deployment: str,
                 azure_openai_endpoint: str,
                 azure_openai_api_key: str,
                 service_id: str = "default"
                 ):
        self.chat_service = AzureChatCompletion(
            deployment_name=azure_openai_deployment,
            endpoint=azure_openai_endpoint,
            api_key=azure_openai_api_key,
            api_version="2024-02-15-preview",
        )
        self.kernel = Kernel()
        self.kernel.add_service(self.chat_service)
        self.context = ConversationContext()
        self.response_generator = ResponseGenerator(self.kernel, self.context)
        self.process_builder = self._build_process()
        self.process = self.process_builder.build()

    def _build_process(self) -> ProcessBuilder:
        process = ProcessBuilder(name="ConversationStateManager")

        shared_context = self.context

        course_plugin = CourseRecommendationPlugin(shared_context)
        student_info_plugin = StudentInfoPlugin(shared_context)
        degree_plugin = DegreeInfoPlugin()

        self.kernel.add_plugin(course_plugin, plugin_name="CourseRecommendationPlugin")
        self.kernel.add_plugin(student_info_plugin, plugin_name="StudentInfoPlugin")
        self.kernel.add_plugin(degree_plugin, plugin_name="DegreeInfoPlugin")

        T = TypeVar("T")

        def create_step(step_class: Type[T]) -> T:
            step = step_class()
            step.kernel = self.kernel
            step.state = shared_context
            return step

        intent_recognition_step = process.add_step(
            IntentRecognitionStep,
            factory_function=lambda: create_step(IntentRecognitionStep),
        )

        state_transition_step = process.add_step(
            StateTransitionProcess,
            factory_function=lambda: create_step(StateTransitionProcess),
        )

        rag_evaluation_step = process.add_step(
            InformationRetrievalEvaluationStep,
            factory_function=lambda: create_step(InformationRetrievalEvaluationStep),
        )

        response_step = process.add_step(
            ResponseStep,
            factory_function=lambda: create_step(ResponseStep),
        )

        degree_planning_validation_step = process.add_step(
            DegreePlanningValidationStep,
            factory_function=lambda: create_step(DegreePlanningValidationStep),
        )

        # Define the process flow
        process.on_input_event(event_id="UserInput").send_event_to(
            intent_recognition_step,
            parameter_name="user_input"
        )

        intent_recognition_step.on_event(event_id="IntentRecognized").send_event_to(
            state_transition_step,
            parameter_name="data"
        )

        intent_recognition_step.on_event(event_id="DegreeIntent").send_event_to(
            degree_planning_validation_step,
            parameter_name="data"
        )

        degree_planning_validation_step.on_event(event_id="DegreePlanningValidationStateChanged").send_event_to(
            state_transition_step,
            parameter_name="data"
        )

        state_transition_step.on_event(event_id="StateChanged").send_event_to(
            rag_evaluation_step,
            parameter_name="data"
        )

        state_transition_step.on_event(event_id="StateUnchanged").send_event_to(
            rag_evaluation_step,
            parameter_name="data"
        )

        rag_evaluation_step.on_event(event_id="RagEvaluated").send_event_to(
            response_step,
            parameter_name="data"
        )

        return process

    async def process_message(self, user_input: str) -> str:
        from semantic_kernel.processes.local_runtime.local_kernel_process import start
        from semantic_kernel.processes.kernel_process.kernel_process_event import KernelProcessEvent

        # Store the current message count before processing
        previous_message_count = len(self.context.messages)
        previous_assistant_messages = [msg for msg in self.context.messages if msg["role"] == "assistant"]

        # Process the message
        async with await start(
                process=self.process,
                kernel=self.kernel,
                initial_event=KernelProcessEvent(id="UserInput", data=user_input)
        ) as running_process:
            # The context is properly awaited here
            pass

        # Now check for new assistant messages (after process completion)
        current_assistant_messages = [msg for msg in self.context.messages if msg["role"] == "assistant"]

        # If a new assistant message was added
        if len(current_assistant_messages) > len(previous_assistant_messages):
            # Return the newest message (the last one)
            message = current_assistant_messages[-1]["content"]
            if message is None:
                return "I'm sorry, I couldn't generate a response. Please try again with the same message."
            return message

        return "I'm sorry, I couldn't generate a response. Please try again with the same message."