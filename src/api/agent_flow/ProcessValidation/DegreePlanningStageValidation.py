from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class DegreePlanningStageValidation:
    def __init__(self, kernel: Kernel, state: ConversationContext):
        self.kernel = kernel
        self.state = state
        self._setup_validation_functions()

    def _setup_validation_functions(self):
        step_validator = PromptTemplateConfig(
            template="""
            You are a Stage Controller for a multi-stage academic advising system. Your sole responsibility is to determine which stage of the degree planning process should be active based on the current conversation state and student information.
            
            # Available Stages
            1. MAIN_ADVISOR - General degree information and initial major selection
            2. BASIC_INFO - Gathering time preferences and course load
            3. CAREER_GOALS - Identifying student goals and recommending relevant courses
            4. REQUIREMENTS - Walking through degree requirements with choices
            5. COMPLETED - All necessary information has been gathered
            
            # Student Information Tracking
            You will have access to all student information gathered so far, including:
            - major
            - degree_type (BA, BS, etc.)
            - preferred_class_times
            - course_load (also called preferred_courses_per_semester)
            - career_goals
            - recommended_courses
            - requirement_preferences
            
            Important: The system may use either 'course_load' or 'preferred_courses_per_semester' field names interchangeably - treat them as the same information.
            
            # Stage Determination Logic
            Determine the appropriate stage using the following logic:
            
            ## MAIN_ADVISOR Stage
            - REMAIN in this stage if:
              * No major has been specified yet
              * A major is specified but needs degree_type clarification (if applicable)
              * The user is asking general questions not related to their specific degree planning
            - REVERT to this stage if:
              * User explicitly changes their major or degree_type at any point in the process
              * User explicitly asks to restart the entire process
            
            ## BASIC_INFO Stage
            - ADVANCE to this stage when:
              * Major and degree_type (if applicable) have been confirmed
              * User has expressed interest in degree planning
              * User has confirmed they want to plan for a newly selected major
            - REMAIN in this stage until:
              * Both preferred_class_times AND course_load have been specified
            - REVERT to this stage if:
              * User explicitly wants to change their time preferences or course load
            
            ## CAREER_GOALS Stage
            - ADVANCE to this stage when:
              * Major, degree_type, preferred_class_times, and course_load are all specified
              * This should trigger IMMEDIATELY after the user provides their course_load, even if they provide it as a simple number (like "4" or "5")
              * Do not wait for additional messages after course_load is specified - move to this stage right away
            - REMAIN in this stage until:
              * career_goals have been identified AND processed
              * At least one recommended_course has been explicitly suggested in the assistant's response
              * The assistant has had an opportunity to respond to the career goal with course recommendations
            - REVERT to this stage if:
              * User explicitly wants to reconsider their career goals or course recommendations
            
            ## REQUIREMENTS Stage
            - ADVANCE to this stage when:
              * All prior information has been collected (major, degree_type, preferred_class_times, course_load, career_goals)
              * At least one recommended_course has been suggested based on the career goal
            - REMAIN in this stage until:
              * All required requirement_preferences have been collected
            - REVERT to this stage if:
              * User wants to change specific requirement choices but not their overall goals
            
            ## COMPLETED Stage
            - ADVANCE to this stage when:
              * All prior stages have been completed
              * User has specified their elective focus areas or categories of interest
              * The conversation has reached a point where all essential planning information has been gathered
              * Specifically, the user has responded to the question about which elective areas or focus areas they want
            - TRANSITION to this stage IMMEDIATELY after the user provides their elective area choices
            
            # Change Detection Logic
            - Major/Degree Change: If user changes major or degree_type, revert to MAIN_ADVISOR
            - Preference Change: If user changes time or course preferences, revert to BASIC_INFO
            - Goal Change: If user changes career goals, revert to CAREER_GOALS
            - Requirement Change: If user changes specific requirements, remain in REQUIREMENTS
            
            # Critical Rules for Major Change
            - When a user changes their major and confirms they want to plan for the new major:
            - If they already have preferred_class_times, IMMEDIATELY move to BASIC_INFO stage
            - If a user says "yes" or affirmatively responds to continuing with a new major, treat this as confirming the major and move to BASIC_INFO
            - Do not stay in MAIN_ADVISOR after a user has confirmed a change of major with "yes" or similar affirmation
            
            # Immediate Progression Rules
            - When both major and degree_type are set, move to BASIC_INFO
            - When both preferred_class_times and course_load are set, move to CAREER_GOALS, without waiting for additional messages
            - When career_goals and at least one recommended_course are set, move to REQUIREMENTS
            - This means you should check all stage progression conditions after EVERY user message
            
            # Completion Detection
            - When the assistant presents elective areas or categories (e.g., "Software Development", "Cybersecurity", etc.) and asks the user to select from them
            - And the user responds with their selection(s) (e.g., "software development and cybersecurity")
            - Then the system should immediately move to COMPLETED stage
            
            # Output Format
            Your response must ONLY contain one of these stage names as a plain string:
            - MAIN_ADVISOR
            - BASIC_INFO
            - CAREER_GOALS  
            - REQUIREMENTS
            - COMPLETED
            
            Do not include any explanations, formatting, or additional text.
            
            Important: If you detect that preferred_class_times and preferred_courses_per_semester (or course_load) are BOTH specified, you MUST return CAREER_GOALS. Do not remain in BASIC_INFO once these two pieces of information are provided.
            
            # Current Student Information
            Use this information to determine the current stage:
            {{$student_info}}
            
            # Missing Fields
            These fields are still needed for a complete degree plan:
            {{$missing_fields}}
            
            # Chat History
            {{$chat_history}}
            
            # Current Message
            {{$user_input}}
            """,
            input_variables=[
                InputVariable(name="user_input", description="The user's input", is_required=True),
                InputVariable(name="chat_history", description="The chat history", is_required=True),
            ]
        )
        self.kernel.add_function(
            plugin_name="DegreeStepValidation",
            function_name="determine_stage",
            prompt_template_config=step_validator,
        )

    async def determine_degree_planning_state(self, user_input: str, missing_fields) -> str:
        if self.state.artifact.current_state != "degree_planning":
            return "Not in degree planning state"

        response = await self.kernel.invoke(
            plugin_name="DegreeStepValidation",
            function_name="determine_stage",
            arguments=KernelArguments(
                user_input=user_input,
                student_info=self.state.artifact,
                chat_history=self.state.to_chat_history().messages,
            )
        )
        if response == "REQUIREMENTS":
            if len(self.state.artifact.courses_selected) == 0:
                print("Degree plan stage validation error - fallback activated")
                response = "CAREER_GOALS"

        if response == "BASIC_INFO":
            if self.state.artifact.preferred_courses_per_semester is not None:
                print("Degree plan stage validation error - fallback activated")
                response = "CAREER_GOALS"



        print(f"missing fields: {missing_fields}")
        print(f"response: {response}")
        return str(response)
