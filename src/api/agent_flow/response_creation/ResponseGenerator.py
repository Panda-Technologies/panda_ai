from semantic_kernel import Kernel
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.functions import KernelArguments, FunctionResult
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext
from src.api.agent_flow.information_search.RagChat import AzureRagChat
from src.api.agent_flow.information_search.SearchQueryProcess import SearchQuery
from src.api.agent_flow.response_creation.DegreeAdvisorPrompt import main_degree_advisor_prompt, \
    basic_info_gather_prompt, career_goal_course_recommendation_prompt, requirements_preference_prompt
from src.api.agent_flow.response_creation.RAGPrompt import rag_prompt


class ResponseGenerator:
    def __init__(self, kernel: Kernel, state: ConversationContext):
        self.initial_prompt = None
        self.course_question_prompt = None
        self.general_prompt = None
        self.kernel = kernel
        self.state = state
        self.main_degree_advisor = main_degree_advisor_prompt
        self.basic_info_gather = basic_info_gather_prompt
        self.career_goal_gather = career_goal_course_recommendation_prompt
        self.requirements_preference_gather = requirements_preference_prompt
        self.setup_response_templates()
        self.setup_response_functions()

    def setup_response_templates(self):
        self.course_question_prompt = PromptTemplateConfig(
            template="""
            You are a scheduling assistant helping generate class schedules.
            Current conversation context:
            - Student name
            - Degree program
            - Current semester
            - Available days
            - Completed courses
            
            Respond to the following message in a helpful way, gathering any missing information 
            that would be helpful for generating a schedule. If you don't have enough information,
            ask targeted questions to gather what you need.
            
            User message: {{$user_input}}
            Chat history: {{$chat_history}}
            
            missing_fields: {{$missing_fields}}
            
            Search results: {{$search_results}}
            """,
            input_variables=[
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="missing_fields", description="Missing fields for generating schedule", is_required=True),
                InputVariable(name="search_results", description="The search results from RAG", is_required=False),
            ],
        )
        self.general_prompt = PromptTemplateConfig(
            template="""
            You are a helpful assistant that specializes in UNC Chapel Hill related information. You can assist with:
            1. General UNC Chapel Hill information (campus resources, history, policies)
            2. Student account information through API access (assignments, tasks, schedules)
            3. Academic information (courses, requirements, deadlines)
            4. Degree information (requirements, etc.). If a user asks for degree information, ask them if they want to degree plan for that degree or not.
            
            IMPORTANT INSTRUCTIONS FOR API QUERIES:
            - When users ask about their personal information (assignments, tasks, schedules, etc.), use the appropriate StudentInfoPlugin functions to retrieve accurate data
            - For follow-up questions using pronouns (e.g., "which ones"), carefully determine what the user is referring to based on context
            - Pay close attention to qualifiers like "completed", "not started", "due soon", etc. as they require different data sets
            - If a request is ambiguous, ask for clarification before returning data
            - After retrieving information, organize it in a clear, structured format
            - **Student-Specific Queries (Assignments, Tasks, Schedules)**
            - If the user asks about **assignments, coursework, due dates, or schedules**, call `StudentInfoPlugin-get_user_info` to retrieve the necessary data.
            - Pay close attention to qualifiers like:
                - *'Do I have any assignments left?'* → Fetch outstanding coursework.
                - *'Which assignments are due soon?'* → Retrieve upcoming deadlines.
                - *'Have I completed my assignments?'* → Filter for completed vs. pending tasks.
            - If the request is unclear, **ask for clarification** before retrieving data.
            
            - **Academic Queries (Courses, Majors, Degree Planning)**
              - If the user asks for degree requirements (e.g., *'What are the CS major requirements?'*), retrieve structured details.
              - **Ask if they want a degree plan** if they request major requirements.
              - Call relevant functions like `StudentInfoPlugin-major_info` or `CourseRecommendationPlugin-add_courses` for course planning.
            
            
            Functions:
            Only functions: ['CourseRecommendationPlugin-add_courses', 'CourseRecommendationPlugin-clear_all_courses', 
            'StudentInfoPlugin-clear_student_major_info', 'StudentInfoPlugin-get_user_info', 'StudentInfoPlugin-career_goals', 
            'StudentInfoPlugin-course_load', 'StudentInfoPlugin-credits_needed', 'StudentInfoPlugin-major_info', 'StudentInfoPlugin-minor_info', 
            'StudentInfoPlugin-summer_availability', 'StudentInfoPlugin-term_info', 'StudentInfoPlugin-time_preference'] are allowed
            
            IMPORTANT INFO ABOUT SEARCH RESULTS:
            - If the user asks a question that can be answered by the search results, use the search results to answer the question
            - If the user asks a question that cannot be answered by the search results, try your best to answer it but make it clear that you are not sure about the answer
            - If there are no search results, that means the user's input does not need search results as that was already decided previously, so answer it normally by ignoring the search results.
            - If there are no search results, don't mention that to the user. Just respond to their input normally and don't be awkward just because there are no search results
            - STOP TRYING TO ANSWER THE QUERY WITH THE SEARCH RESULTS IF THERE ARE NO SEARCH RESULTS AND DO NOT TELL THE USER ABOUT THE SEARCH RESULTS
            
            ### **🚨 Critical Fixes for Function Calls**
            - **Every query should be treated as a distinct request, even if related to the last one.**
            - **DO NOT repeat previous responses unless explicitly requested.**
            - **For follow-up queries, modify the response based on the user’s latest input:**
              - If the user asks: *"Which one is due the soonest?"* → Return **only that assignment** instead of listing all assignments again.
              - If the user asks: *"Which ones are already complete?"* → Filter and return **only completed assignments**.
              - If the user asks: *"Which assignments should I start today?"* → Filter and return **only assignments with today’s due date**.
            
            ---
            
            ### **🔥 API Query Handling**
            #### **Student-Specific Queries (Assignments, Tasks, Schedules)**
            | **User Input** | **Expected Action** |
            |----------------|---------------------|
            | *"What assignments are due soon?"* | **Trigger `StudentInfoPlugin-get_user_info`** (Retrieve full assignment list) |
            | *"Which assignment is due first?"* | **Trigger `StudentInfoPlugin-get_user_info` again** (Sort by earliest due date) |
            | *"Do I have any overdue assignments?"* | **Trigger `StudentInfoPlugin-get_user_info` with overdue filter** |
            | *"Which classes have assignments left?"* | **Trigger `StudentInfoPlugin-get_user_info` with class grouping** |
            
            ---
    
            
            ### **🔄 Chat History Handling Fix**
            - **DO NOT copy and paste old responses verbatim.**
            - **Use chat history for reference only, not for repetition.**
            - **Only return new, relevant information for each query.**
            
            ---
            
            User message: {{$user_input}}
            
            ---
            
            Chat history: {{$chat_history}}
            
            ---
            
            Search results: {{$search_results}}
            """,
            input_variables=[
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="search_results", description="The search results from RAG", is_required=False),
            ],
        )
        self.initial_prompt = PromptTemplateConfig(
            template="""
            You are a helpful assistant that will try to understand a user's intent to contacting you,
            an academic advisor at UNC Chapel Hill. Users can ask you questions about degree planning, course scheduling,
            or any other general UNC related questions.
            
            User message: {{$user_input}}
            
            Search results: {{$search_results}}
            """,
            input_variables=[
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="search_results", description="The search results from RAG", is_required=False),
            ]
        )

    def setup_response_functions(self):
        execution_settings = AzureChatPromptExecutionSettings()
        execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto(
            filters={"included_plugins": ["StudentInfoPlugin", "CourseRecommendationPlugin"]},
            auto_invoke=True
        )

        self.kernel.add_function(
            plugin_name="DegreePlanning",
            function_name="main_degree_advisor",
            prompt_template_config=self.main_degree_advisor,
            prompt_execution_settings=execution_settings,
        )
        self.kernel.add_function(
            plugin_name="DegreePlanning",
            function_name="basic_info_gather",
            prompt_template_config=self.basic_info_gather,
            prompt_execution_settings=execution_settings,
        )
        self.kernel.add_function(
            plugin_name="DegreePlanning",
            function_name="career_goal_gather",
            prompt_template_config=self.career_goal_gather,
            prompt_execution_settings=execution_settings,
        )
        self.kernel.add_function(
            plugin_name="DegreePlanning",
            function_name="requirements_gather",
            prompt_template_config=self.requirements_preference_gather,
            prompt_execution_settings=execution_settings,
        )
        self.kernel.add_function(
            plugin_name="CourseQuestion",
            function_name="course_question",
            prompt_template_config=self.course_question_prompt,
            prompt_execution_settings=execution_settings,
        )
        self.kernel.add_function(
            plugin_name="General",
            function_name="general",
            prompt_template_config=self.general_prompt,
            prompt_execution_settings=execution_settings,
        )
        self.kernel.add_function(
            plugin_name="Initial",
            function_name="initial",
            prompt_template_config=self.initial_prompt,
            prompt_execution_settings=execution_settings,
        )

    async def generate_response(self, state: ConversationContext, user_input: str, retrieval_type: str, arguments: KernelArguments, degree_plan_step: str | None) -> FunctionResult | None:
        arguments["user_input"] = user_input
        prompt_config: PromptTemplateConfig
        plugin_name: str
        function_name: str

        match state.artifact.current_state:
            case "degree_planning":
                plugin_name = "DegreePlanning"
                match degree_plan_step:
                    case "BASIC_INFO":
                        function_name = "basic_info_gather"
                    case "CAREER_GOALS":
                        function_name = "career_goal_gather"
                    case "REQUIREMENTS":
                        function_name = "requirements_gather"
                    case "MAIN_ADVISOR":
                        function_name = "main_degree_advisor"
                    case _:
                        function_name = "main_degree_advisor"
            case "course_question":
                plugin_name = "CourseQuestion"
                function_name = "course_question"
            case "general_qa":
                plugin_name = "General"
                function_name = "general"
            case "initial":
                plugin_name = "Initial"
                function_name = "initial"
            case _:
                plugin_name = "Initial"
                function_name = "initial"
        if retrieval_type == "rag" or retrieval_type == "web":
            print("RAG")
            query = await SearchQuery(kernel=self.kernel, state=self.state).generate_search_query(user_input=user_input, retrieval_type=retrieval_type)
            search_results = await AzureRagChat(state=state, kernel=self.kernel, query=query, retrieval_type=retrieval_type, prompt_template=rag_prompt).generate_response()
            arguments["search_results"] = search_results
            print(f"search_results: {search_results}")
        try:
            response = await self.kernel.invoke(
                plugin_name=plugin_name,
                function_name=function_name,
                arguments=arguments,
            )
            return response
        except Exception as e:
            print(f"Function failed. Error: {e}")
            return None
