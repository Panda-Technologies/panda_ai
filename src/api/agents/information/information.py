from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ConnectionType
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import prompty
import json
from dotenv import load_dotenv
import logging
import tiktoken  # Ensure this is installed: pip install tiktoken

load_dotenv()

# Initialize logging and tracing
logger = logging.getLogger(__name__)


def get_search_terms(context: Dict) -> List[str]:
    """Extract specific search terms from context for any major/department"""
    search_terms = []

    # Extract major and degree type info
    major = None
    degree_type = None

    if isinstance(context, dict):
        # Get data from the correct structure
        if isinstance(context, dict) and 'data' in context:
            data = context['data']
            initial_info = data.get('initialInfo', {})
            topic = initial_info.get('topic', '').lower()
            major = initial_info.get('major')

            # Check for degree type in both places
            degree_type = initial_info.get('degreeType')
            if not degree_type:
                # Look for degree type in topic/query
                lower_topic = topic.lower()
                if 'bs' in lower_topic or 'b.s.' in lower_topic:
                    degree_type = 'BS'
                elif 'ba' in lower_topic or 'b.a.' in lower_topic:
                    degree_type = 'BA'

            # Try to extract major from topic if not directly provided
            if not major and topic:
                # Clean topic to extract potential major
                topic_cleaned = topic.replace('requirements', '').replace('major', '').strip()
                if topic_cleaned:
                    words = topic_cleaned.split()
                    # Handle things like "cs" -> "Computer Science"
                    if topic_cleaned.lower() == 'cs':
                        major = 'Computer Science'
                    else:
                        major = ' '.join(words).title()

    # Format search terms if we have major info
    if major:
        major = major.strip()
        # Base queries
        search_terms.append(f"{major} Major")
        search_terms.append(f"{major} Program Requirements UNC")

        # Degree-specific queries
        if degree_type:
            search_terms.extend([
                f"{major} {degree_type} Requirements UNC",
                f"{major} {degree_type} Degree Requirements",
                f"{major} {degree_type} Major Core Requirements",
                f"{major} {degree_type} Curriculum"
            ])

        # Department queries
        if major.lower() == "computer science":
            search_terms.extend([
                "COMP Major Requirements",
                f"COMP {degree_type} Requirements" if degree_type else "COMP Requirements"
            ])

        # Add specific page number queries if known
        known_pages = {
            "Computer Science BS": "478",
            "Computer Science BA": "475"
        }
        key = f"{major} {degree_type}" if degree_type else major
        if page := known_pages.get(key):
            search_terms.append(f"{page} {major} Major")

    print(f"Generated search terms: {search_terms}")  # Debug print
    return search_terms

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

        # Initialize search client
        self.search_client = SearchClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
        )

    def split_text_into_chunks(self, text: str, chunk_size: int = 512, overlap: int = 50,
                               model_name: str = "gpt-4o-mini") -> List[str]:
        encoding = tiktoken.encoding_for_model(model_name)
        sentences = text.split('. ')
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_tokens = encoding.encode(sentence + '.')
            sentence_size = len(sentence_tokens)

            # If adding this sentence would exceed chunk size
            if current_size + sentence_size > chunk_size and current_chunk:
                # Create chunk with current sentences
                chunks.append(' '.join(current_chunk))

                # Start new chunk with overlap from previous chunk
                overlap_buffer = current_chunk[-2:]  # Keep last 2 sentences for overlap
                current_chunk = overlap_buffer[:]  # Copy overlap sentences to new chunk

                # Recalculate size with overlap sentences
                current_size = sum(len(encoding.encode(s)) for s in current_chunk)

            current_chunk.append(sentence + '.')
            current_size += sentence_size

        # Add the last chunk if there's anything left
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    async def get_embeddings(self, texts: List[str]) -> List[Dict[str, any]]:
        """
        Generate embeddings for academic search queries.
        """
        try:
            all_embeddings = []
            for text in texts:
                chunks = self.split_text_into_chunks(text)
                for chunk in chunks:
                    embeddings_response = self.embeddings.embed(
                        model=os.environ["EMBEDDINGS_MODEL"],
                        input=chunk
                    )
                    all_embeddings.append({
                        "query": chunk,
                        "embedding": embeddings_response.data[0].embedding
                    })
            return all_embeddings
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            raise

    async def search_academic_info(self, items: List[Dict[str, any]], top_k: int = 3) -> Dict[str, any]:
        try:
            all_results = {}
            for item in items:
                query_key = item.get("query", str(item))
                if isinstance(query_key, dict):
                    query_key = str(query_key)

                vector_query = VectorizedQuery(
                    vector=item["embedding"],
                    k_nearest_neighbors=top_k,
                    fields="contentVector"
                )

                results = self.search_client.search(
                    search_text=query_key,
                    vector_queries=[vector_query],
                    select=["id", "content", "title", "url"],
                    top=top_k
                )

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


async def find_academic_info(context: Dict[str, any] | str) -> Dict[str, any]:
    """Main function to find academic information based on context."""
    try:
        # Extract search context and terms
        search_terms = get_search_terms(context) if isinstance(context, dict) else []

        print(f"context: {context}, search_terms: {search_terms}")

        # Generate queries using prompty
        raw_queries = prompty.execute(
            "information.prompty",
            inputs={
                "context": context if isinstance(context, str) else json.dumps(context),
                "chat_history": context.get("chat_history", []) if isinstance(context, dict) else [],
                "conversation_state": context.get("conversation_state", {}) if isinstance(context, dict) else {}
            }
        )

        # Combine specific terms and prompty queries
        search_queries = set(search_terms)  # Use set to remove duplicates
        try:
            if isinstance(raw_queries, str):
                parsed_queries = json.loads(raw_queries)
                if isinstance(parsed_queries, dict) and "queries" in parsed_queries:
                    search_queries.update(parsed_queries["queries"])
                elif isinstance(parsed_queries, list):
                    search_queries.update(parsed_queries)
            elif isinstance(raw_queries, dict):
                if "queries" in raw_queries:
                    search_queries.update(raw_queries["queries"])
            elif isinstance(raw_queries, list):
                search_queries.update(raw_queries)
        except json.JSONDecodeError:
            logging.warning("Failed to parse prompty queries")
            if search_queries:  # If we have explicit terms, continue with those
                pass
            else:  # Otherwise, use raw query as fallback
                search_queries = {str(raw_queries)}

        search_queries = list(filter(None, search_queries))  # Remove empty queries

        if not search_queries:
            raise ValueError("No valid search queries generated")

        # Log the queries we're using
        logging.info(f"Search queries: {search_queries}")

        # Initialize search client and get results
        search_client = AcademicInfoSearch()
        embedded_items = await search_client.get_embeddings(search_queries)
        if not embedded_items:
            raise ValueError("No embeddings generated")

        # Perform search and process results
        results = await search_client.search_academic_info(embedded_items)

        # Process and categorize results
        processed_results = {
            "courses": [],
            "requirements": [],
            "programs": [],
            "raw_results": results
        }

        # Categorize search results
        for query_results in results.values():
            for result in query_results:
                # Extract course info
                if any(word in result['content'].lower() for word in ['course', 'comp', 'prerequisites']):
                    processed_results['courses'].append(result)
                # Extract requirement info
                elif 'requirement' in result['content'].lower():
                    processed_results['requirements'].append(result)
                # General program info
                else:
                    processed_results['programs'].append(result)

        return processed_results

    except Exception as e:
        logging.error(f"Error finding academic info: {e}")
        logging.error(f"Error details: {str(e)}", exc_info=True)
        raise