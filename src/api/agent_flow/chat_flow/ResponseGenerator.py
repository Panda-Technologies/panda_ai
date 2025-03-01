from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

class ResponseGenerator:
    def __init__(self, kernel):
        self.kernel = kernel
        self.setup_response_functions()

    def setup_response_functions(self):
        degree_planning_prompt = PromptTemplateConfig(
            template="""
        You are an academic advisor helping with degree planning.
        Current conversation context:
        - Student name: {{$student_name or "Unknown"}}
        - Degree program: {{$degree_program or "Unknown"}}
        - Completed courses: {{$completed_courses or "None"}}
        - Graduation year: {{$grad_year or "Unknown"}}
        - Interests: {{$interests or "None specified"}}
        
        Respond to the following message in a helpful way, gathering any missing information 
        that would be helpful for degree planning. If you don't know the answer, it's okay to say so.
        If the student hasn't specified a degree program, gently ask what program they're interested in.
        
        User message: {{$user_input}}
        Chat history: {{$chat_history}}
            """,
            input_variables=[
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="user_input", description="The user input", is_required=True),
            ],
        )

        self.kernel.add_function(
            plugin_name="DegreeAdvisor",
            function_name="get_response",
            prompt_template_config=degree_planning_prompt
        )

