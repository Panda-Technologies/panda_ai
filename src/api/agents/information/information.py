import os
from pathlib import Path
from typing import List, Dict

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType
import prompty
import json
from dotenv import load_dotenv
import logging

load_dotenv()

# Initialize logging and tracing
logger = logging.getLogger(__name__)

class AcademicInfoSearch:
    def __init__(self):
        # Create project client
        self.project = AIProjectClient.from_connection_string(
            conn_str=os.environ["AIPROJECT_CONNECTION_STRING"],
            credential=DefaultAzureCredential()
        )

        # Get clients from project
        self.embeddings = self.project.inference.get_embeddings_client()
        self.chat = self.project.inference.get_chat_completions_client()

        # Get search connection from project
        search_connection = self.project.connections.get_default(
            connection_type=ConnectionType.AZURE_AI_SEARCH,
            include_credentials=True
        )

        # Initialize search client
        self.search_client = SearchClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
        )

    async def get_embeddings(self, texts: List[str]) -> List[Dict[str, any]]:
        """Generate embeddings for academic search queries"""
        try:
            # OpenAI expects a specific format for embeddings
            embeddings_response = self.embeddings.embed(model=os.environ["EMBEDDINGS_MODEL"], input=texts if isinstance(texts, str) else [str(text) for text in texts])

            # Process response
            return [
                {"query": texts[i], "embedding": embeddings_response.data[i].embedding}
                for i in range(len(texts))
            ]
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            print(f"Texts causing error: {texts}")  # Debug print
            raise

    async def search_academic_info(self, items: List[Dict[str, any]], top_k: int = 3) -> Dict[str, any]:
        try:
            all_results = {}
            for item in items:
                # Make sure we have a string query to use as key
                query_key = item.get("query", str(item))  # Fallback to string representation if no query
                if isinstance(query_key, dict):
                    query_key = str(query_key)  # Convert dict to string if needed

                vector_query = VectorizedQuery(
                    vector=item["embedding"],
                    k_nearest_neighbors=top_k,
                    fields="contentVector"
                )

                # Perform the search
                results = self.search_client.search(
                    search_text=query_key,
                    vector_queries=[vector_query],
                    select=["id", "content", "title", "url"],
                    top=top_k
                )

                # Store results using string key
                all_results[query_key] = [
                    {
                        "id": doc["id"],
                        "title": doc["title"],
                        "content": doc["content"],
                        "url": doc.get("url", ""),
                        "relevance_score": getattr(doc, "@search.score", 0),
                    }
                    for doc in results
                ]

            return all_results

        except Exception as e:
            logging.error(f"Error searching academic info: {e}")
            raise


async def find_academic_info(context: str) -> Dict[str, any]:
    """Main function to find academic information based on context"""
    try:
        # Get specialized search queries from prompty
        queries = prompty.execute("information.prompty", inputs={"context": context})
        try:
            search_queries = json.loads(queries)
            if not isinstance(search_queries, list):
                raise ValueError("Expected list of queries")
            if not all(isinstance(q, str) for q in search_queries):
                raise ValueError("All queries must be strings")

            # Make sure we have at least one query
            if not search_queries:
                search_queries = [context]  # Use original context if no queries generated

            # Ensure all queries are strings and not empty
            search_queries = [str(q).strip() for q in search_queries if q]
            print(f'broken query {search_queries}')
            if not search_queries:
                raise ValueError("No valid queries generated")

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse queries: {e}")
            search_queries = [context]  # Fallback to original context

        # Initialize search client
        search_client = AcademicInfoSearch()

        # Generate embeddings for queries
        try:
            embedded_items = await search_client.get_embeddings(search_queries)
            if not embedded_items:
                raise ValueError("No embeddings generated")
        except Exception as e:
            logging.error(f"Error in embeddings generation: {e}")
            raise

        # Search for academic information
        results = await search_client.search_academic_info(embedded_items)
        return results


    except Exception as e:
        logging.error(f"Error in embeddings generation: {e}")
        raise
