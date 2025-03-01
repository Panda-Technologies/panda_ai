import logging
from typing import Optional, Tuple, List

from pydantic import SecretStr

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
)
from semantic_kernel.connectors.memory.azure_cognitive_search.azure_ai_search_settings import AzureAISearchSettings
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import KernelArguments, FunctionResult
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
from ..information_search.RagChat import AzureRagChat


def extract_citations(response: str) -> List[str]:
    """Extract citations from response if present."""
    citations = []
    if "[doc" in response:
        import re
        citations = re.findall(r'\[doc\d+\]', response)
    return citations

class IntelligentChatClient:
    def __init__(self,
                 azure_openai_deployment: str,
                 azure_openai_endpoint: str,
                 azure_openai_api_key: str,
                 azure_search_endpoint: str,
                 azure_search_api_key: str,
                 azure_search_index: str):

        self.kernel = Kernel()
        logging.basicConfig(level=logging.INFO)

        # Initialize Azure OpenAI Chat Service
        self.chat_service = AzureChatCompletion(
            deployment_name=azure_openai_deployment,
            endpoint=azure_openai_endpoint,
            api_key=azure_openai_api_key,
            api_version="2024-02-15-preview"
        )
        self.kernel.add_service(self.chat_service)

        # Initialize Azure Cognitive Search settings
        self.azure_ai_search_settings = AzureAISearchSettings(
            endpoint=azure_search_endpoint,
            index_name=azure_search_index,
            api_key=SecretStr(azure_search_api_key),
        )

        self.chat_history = ChatHistory()
        self.chat_history.add_system_message(
            "I am an AI assistant that can access external knowledge when needed to provide accurate information."
        )

        # Set up prompt templates with execution_settings so that RAG retrieval is applied
        self._setup_prompt_templates()

        # Add chat functions only once so the configuration isn’t lost.
        self.standard_chat_function = self.kernel.add_function(
            plugin_name="ChatBot",
            function_name="Chat",
            prompt_template_config=self.standard_template_config
        )
        self.rag_chat_function = self.kernel.add_function(
            plugin_name="ChatBot",
            function_name="Chat",
            prompt_template_config=self.rag_template_config
        )

    def _setup_prompt_templates(self):
        """Setup the various prompt templates needed for different operations,
        embedding the execution settings that trigger retrieval augmentation."""
        # Template for standard chat
        self.standard_template_config = PromptTemplateConfig(
            template="{{$chat_history}}\nUser: {{$user_input}}\nAssistant:",
            name="standard_chat",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="user_input", description="The user input", is_required=True),
            ]
        )

        # Template for RAG chat: note that while we include a slot for search_results,
        # the key is to have execution_settings inject the full retrieved context.
        self.rag_template_config = PromptTemplateConfig(
            template="""Use the provided context to answer the user's question.
Be specific and cite sources when appropriate. If you cannot find the answer from RAG, compare your results with the search results and use those if needed.
If the context doesn't contain relevant information, say so.

Previous context: {{$chat_history}}
Search context: {{$search_results}}
User: {{$user_input}}
Assistant:""",
            name="rag_chat",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="chat_history", description="The chat history", is_required=True),
                InputVariable(name="search_results", description="Results from search", is_required=True),
                InputVariable(name="user_input", description="The user input", is_required=True),
            ]
        )

        # Template for RAG evaluation remains unchanged.
        self.evaluation_template_config = PromptTemplateConfig(
            template="""Evaluate if the following user query requires accessing external knowledge or if it can be 
            answered using general knowledge. Respond with either 'true' or 'false'. You must always answer with 'true' 
            when a specific degree or class is mentioned by name such as "computer science, biology, chemistry, etc." 
            However, do not answer with 'true' if the user requests to just plan a degree. Also, use the chat history as
            context to determine if the user query requires external knowledge. However, ensure you are not just looking at the
            chat history to determine if external knowledge is needed, but rather the context of the chat history in relation to the user query.
            
            
            User query: {{$user_input}}
            
            Chat history: {{$chat_history}}
            
            Consider:
            1. Does this require specific factual information?
            2. Does this ask about particular documents or data?
            3. Is this something that requires current or historical context?
            4. Is this mentioning or discussing a specific degree or class? If so, then it likely requires external knowledge.
            5. Anything UNC related should be marked as 'true'.
            6. If the user is asking for any financial aid or scholarships information, it should be marked as 'true'.
            """,
            name="rag_evaluation",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="chat_history", description="The chat history", is_required=True),
            ]
        )

        # Template for search query generation remains unchanged.
        self.search_query_template_config = PromptTemplateConfig(
            template="""Analyze the user's question and create an optimal search query for UNC Chapel Hill information. 

            USER INPUT: {{$user_input}}

            CHAT HISTORY: {{$chat_history}}

            SEARCH QUERY RULES:
            1. Focus on UNC-specific terminology and context
            2. Include official UNC department names, course designations, and program terms
            3. Expand common UNC acronyms (e.g., "CS" → "Computer Science")
            4. Translate general academic terms to UNC-specific equivalents:
               - "courses before applying to major" → "gateway courses prerequisites major requirements"
               - "financial aid" → "UNC Chapel Hill scholarships grants FAFSA CSS Profile"
               - "housing" → "UNC residence halls dormitories on-campus housing"
               - "majors" → "UNC undergraduate degree programs majors minors"
               - "registration" → "UNC ConnectCarolina course registration enrollment appointment"
            5. Add "UNC Chapel Hill" context for general queries
            6. Do NOT use chat history for context if the current query is a new topic
            7. Prioritize search terms that match UNC website structure and metadata
            8. Avoid having site:unc.edu in the query

            Create a search query with precise keywords that would return the most accurate results. Return ONLY the optimized search query text with no explanation or other text.

            SEARCH QUERY:""",
            name="search_query",
            template_format="semantic-kernel",
            input_variables=[
                InputVariable(name="user_input", description="The user input", is_required=True),
                InputVariable(name="chat_history", description="The chat history", is_required=True),
            ]
        )

    async def evaluate_rag_need(self, user_input: str) -> Tuple[bool, Optional[str]]:
        """Evaluate if RAG is needed and generate a search query if it is."""
        eval_function = self.kernel.add_function(
            plugin_name="RagEval",
            function_name="Evaluate",
            prompt_template_config=self.evaluation_template_config
        )

        response = await self.kernel.invoke(
            eval_function,
            arguments=KernelArguments(user_input=user_input)
        )
        needs_rag = str(response).strip().lower() == "true"
        print(f"RAG needs to answer: {needs_rag}")

        search_query = None
        if needs_rag:
            query_function = self.kernel.add_function(
                plugin_name="RagEval",
                function_name="GenerateQuery",
                prompt_template_config=self.search_query_template_config
            )
            search_query = await self.kernel.invoke(
                query_function,
                arguments=KernelArguments(user_input=user_input, chat_history=self.chat_history)
            )
            search_query = str(search_query).strip()

        return needs_rag, search_query

    async def perform_rag_search(self, search_query: str) -> FunctionResult | None:
        """Perform a search using Azure AI Search.
        The execution_settings here trigger the retrieval that produces a full context."""
        rag_chat = AzureRagChat()
        search_response = await rag_chat.generate_response(search_query, self.chat_history)
        print('search response:',search_query)
        return search_response

    async def generate_response(
            self,
            user_input: str,
            rag_results: Optional[str] = None
    ) -> str:
        """Generate a response using either RAG results or standard chat.
        Note: We now reuse functions that already have the correct execution_settings."""
        if rag_results:
            print('RAG results:',rag_results)
            arguments = KernelArguments(
                chat_history=str(self.chat_history),
                user_input=user_input,
                search_results=rag_results
            )
            response = await self.kernel.invoke(self.rag_chat_function, arguments=arguments)
        else:
            print('No RAG results')
            arguments = KernelArguments(
                chat_history=str(self.chat_history),
                user_input=user_input
            )
            response = await self.kernel.invoke(self.standard_chat_function, arguments=arguments)
        return str(response)

    async def process_message(self, user_input: str) -> Tuple[str, bool, Optional[List[str]]]:
        """Process a user message and return the response along with RAG info."""
        # First evaluate if we need RAG.
        needs_rag, search_query = await self.evaluate_rag_need(user_input)

        if needs_rag and search_query:
            # Perform RAG search to obtain a detailed retrieval context.
            search_results = await self.perform_rag_search(search_query)
            response = await self.generate_response(user_input, search_results)
        else:
            response = await self.generate_response(user_input)

        # Update chat history.
        self.chat_history.add_user_message(user_input)
        self.chat_history.add_assistant_message(response)

        # Extract citations if RAG was used.
        citations = extract_citations(response) if needs_rag else None

        return response, needs_rag, citations