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
            You are an AI assistant that generates specialized search queries based on the conversation history and current user input. Your task is to create the most relevant search query optimized for the specific retrieval type needed (RAG or web).
            
            ## CRITICAL INSTRUCTIONS ##
            1. ALWAYS generate a proper search query - NEVER apologize or ask questions
            2. If user input is unclear, use information from the conversation artifact when available
            3. For ambiguous queries, generate a basic search term based on the retrieval type and available context
            4. Optimize your query differently based on whether RAG or web search is needed
            
            ## Query Formatting Guidelines ##
            - Format as a search query with keywords, not a question or sentence
            - Use 3-8 keywords in a logical order
            - Include specific details when mentioned (e.g., course codes, professional schools)
            
            ## RAG QUERY STRUCTURE (When retrieval_type = "rag") ##
            - Include "UNC" or "University of North Carolina" in EVERY RAG query
            - For degree planning: "UNC [major] [degree type] requirements courses planning"
            - For career paths: "UNC [major] [career] pathways opportunities" 
            - For premed specifically: "UNC [major] BS requirements courses planning career premed"
            - For other pre-professional tracks: "UNC [major] [pre-professional track] requirements courses"
            - For specific courses: "UNC [course code] description prerequisites"
            - For general questions: "UNC [topic] information resources"
            - If completely uncertain, default to "UNC academic advising general information"
            
            ## WEB QUERY STRUCTURE (When retrieval_type = "web") ##
            - DO NOT include "UNC" unless specifically asking about UNC's relationship with external requirements
            - For medical school: "[medical school] prerequisites requirements admission MCAT"
            - For dental school: "[dental school] prerequisites requirements admission DAT"
            - For pharmacy school: "[pharmacy school] prerequisites PharmD requirements PCAT"
            - For law school: "[law school] prerequisites requirements admission LSAT"
            - For veterinary school: "[veterinary school] prerequisites requirements admission GRE"
            - For other graduate programs: "[program type] application requirements prerequisites GRE"
            - For certifications: "[certification name] requirements preparation exam"
            - For standardized tests: "[test name] preparation requirements scores"
            - For general professional pathways: "[profession] education path requirements licensure"
            - If completely uncertain, default to "pre-professional academic requirements"
            
            ## EXAMPLES ##
            - RAG Query for "What can I do with a computer science degree?": "UNC computer science career pathways opportunities industry"
            - RAG Query for "Tell me about COMP 110": "UNC COMP 110 description prerequisites"
            - Web Query for "What do I need for med school?": "medical school prerequisites requirements admission MCAT"
            - Web Query for "How do I prepare for pharmacy school?": "pharmacy school prerequisites PharmD requirements PCAT"
            
            ## SPECIAL CASES ##
            - For multi-subject queries (e.g., asking about multiple course requirements at once):
              - Combine subjects into a single concise query: "UNC [subject1] [subject2] [subject3] courses requirements planning"
              - Limit to 6-8 keywords total
              - DO NOT repeat terms like "courses" or "requirements" for each subject
              - Example: "What courses satisfy biology, physics, and chemistry requirements?" → "UNC biology physics chemistry courses requirements planning"
            
            ## Context From Conversation Artifact ##
            (Use this information for ambiguous queries)
            State: {{$state}}
            
            User Input: {{$user_input}}
            Chat History: {{$chat_history}}
            
            ## Retrieval Type ##
            Retrieval Type: {{$retrieval_type}}
            
            YOUR RESPONSE MUST BE ONLY THE SEARCH QUERY TERMS. DO NOT INCLUDE ANY EXPLANATIONS, QUESTIONS, OR APOLOGIES.
            """,
            input_variables=[
                InputVariable(name="user_input", description="User input", is_required=True),
                InputVariable(name="chat_history", description="Chat history", is_required=True),
                InputVariable(name="state", description="State", is_required=True),
                InputVariable(name="retrieval_type", description="Retrieval type", is_required=True),
            ]
        )
        self.kernel.add_function(
            plugin_name="SearchQuery",
            function_name="generate_search_query",
            prompt_template_config=search_query_prompt,
        )

    async def generate_search_query(self, user_input: str, retrieval_type: str) -> str:
        response = await self.kernel.invoke(
            plugin_name="SearchQuery",
            function_name="generate_search_query",
            arguments=KernelArguments(
                user_input=user_input,
                chat_history=self.state.to_chat_history(),
                state=str(self.state.model_dump_json()),
                retrieval_type=retrieval_type,
            )
        )
        if response is None:
            raise Exception("Failed to generate search query")
        print(f"search query {str(response)}")
        return str(response)
