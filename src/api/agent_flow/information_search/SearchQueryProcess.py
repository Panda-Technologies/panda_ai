from typing import Dict, Any

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig, InputVariable

from src.api.agent_flow.chat_flow.ConversationContext import ConversationContext


class SearchQuery:

    def __init__(self, kernel: Kernel, state: ConversationContext):
        self.state = state
        self.kernel = kernel
        self._setup_search_function()


    def _setup_search_function(self):
        search_query_prompt = PromptTemplateConfig(
            template="""
            You are an AI assistant that generates specialized search queries for UNC-related topics. 
            Your task is to create the most relevant search query based on the conversation history and current user input.

            ## CRITICAL INSTRUCTIONS ##
            1. ALWAYS generate a proper search query - NEVER apologize or ask questions
            2. If user input is unclear, use information from the conversation artifact when available
            3. For ambiguous queries, generate a basic UNC-related search term based on:
               - Major/degree information from conversation history
               - General academic advising if no specific topic is clear
            4. If completely uncertain, default to "UNC academic advising general information"

            ## Query Formatting Guidelines ##
            - Include "UNC" or "University of North Carolina" in EVERY query
            - Format as a search query with keywords, not a question or sentence
            - Use 3-8 keywords in a logical order
            - Include specific course codes when mentioned (e.g., COMP 110)
            - Focus on academics, requirements, careers, or campus resources

            ## Query Structure ##
            For degree planning: "UNC [major] [degree type] requirements courses planning"
            For career paths: "UNC [major] [career] pathways courses"
            For specific courses: "UNC [course code] description prerequisites"
            For general questions: "UNC [topic] information resources"
            
            ## Context From Conversation Artifact ##
            (Use this information for ambiguous queries)
            State: {{$state}}
            
            User Input: {{$user_input}}
            Chat History: {{$chat_history}}
            
            YOUR RESPONSE MUST BE ONLY THE SEARCH QUERY TERMS. DO NOT INCLUDE ANY EXPLANATIONS, QUESTIONS, OR APOLOGIES.
            """,
            input_variables=[
                InputVariable(name="user_input", description="User input", is_required=True),
                InputVariable(name="chat_history", description="Chat history", is_required=True),
                InputVariable(name="state", description="State", is_required=True),
            ]
        )
        self.kernel.add_function(
            plugin_name="SearchQuery",
            function_name="generate_search_query",
            prompt_template_config=search_query_prompt,
        )

    async def generate_search_query(self, user_input: str) -> str:
        response = await self.kernel.invoke(
            plugin_name="SearchQuery",
            function_name="generate_search_query",
            arguments=KernelArguments(
                user_input=user_input,
                chat_history=self.state.to_chat_history(),
                state=str(self.state.model_dump_json()),
            )
        )
        if response is None:
            raise Exception("Failed to generate search query")
        print(f"search query {str(response)}")
        return str(response)