from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any

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

def validate_queries(queries_data: Dict[str, Any], expected_major: str) -> Dict[str, Any]:
    """Validate and correct queries to ensure they use the exact major name."""
    if not queries_data:
        # Create a default structure if queries_data is None or empty
        return {
            "queries": [
                f"{expected_major} requirements UNC",
                f"{expected_major} major requirements",
                f"{expected_major} program requirements",
                f"{expected_major} required courses"
            ],
            "focus_areas": [
                "Major Requirements",
                "Program Structure",
                "Course Requirements"
            ],
            "context": {
                "major": expected_major,
                "degree_type": None,
                "specialization": None
            },
            "topic": ""  # Default empty topic
        }

    # Ensure context is a dictionary
    if isinstance(queries_data.get("context"), str):
        queries_data["context"] = {
            "major": expected_major,
            "degree_type": None,
            "specialization": None
        }
    elif not isinstance(queries_data.get("context"), dict):
        queries_data["context"] = {
            "major": expected_major,
            "degree_type": None,
            "specialization": None
        }

    # Check and correct context major
    if queries_data["context"].get("major") != expected_major:
        queries_data["context"]["major"] = expected_major

    # Validate and correct queries
    if "queries" in queries_data:
        corrected_queries = []
        for query in queries_data["queries"]:
            if expected_major not in query:
                # Replace any major-like terms with the expected major
                corrected_query = query
                for word in ["Psychology", "Computer Science", "Biology", "Chemistry"]:
                    if word in query:
                        corrected_query = query.replace(word, expected_major)
                        break
                corrected_queries.append(corrected_query)
            else:
                corrected_queries.append(query)
        queries_data["queries"] = corrected_queries

    # Filter queries for requirements if that's the topic
    topic = queries_data.get("topic", "")
    if topic and isinstance(topic, str) and "requirements" in topic.lower():
        requirement_queries = [
            q for q in queries_data.get("queries", [])
            if any(term in q.lower() for term in ["requirement", "curriculum", "course", "program", "major"])
        ]
        if requirement_queries:
            queries_data["queries"] = requirement_queries

    # Ensure queries array exists and has content
    if "queries" not in queries_data or not queries_data["queries"]:
        queries_data["queries"] = [
            f"{expected_major} requirements UNC",
            f"{expected_major} major requirements",
            f"{expected_major} program requirements",
            f"{expected_major} required courses"
        ]

    # Validate focus areas
    if "focus_areas" not in queries_data or not isinstance(queries_data["focus_areas"], list):
        queries_data["focus_areas"] = [
            "Major Requirements",
            "Program Structure",
            "Course Requirements"
        ]

    # Ensure topic exists
    if "topic" not in queries_data:
        queries_data["topic"] = ""

    return queries_data

async def find_academic_info(context: Dict[str, any] | str) -> Dict[str, any]:
    """Main function to find academic information based on context."""
    try:
        # Extract and format the context for the template
        formatted_context = {
            "current_request": {
                "major": None,
                "topic": None,
                "degree_type": None,
                "category": None
            }
        }

        if isinstance(context, dict):
            if 'initialInfo' in context:
                formatted_context["current_request"].update({
                    "major": context['initialInfo'].get('major'),
                    "topic": context['initialInfo'].get('topic'),
                    "category": context['initialInfo'].get('category'),
                    "degree_type": context['initialInfo'].get('degreeType')
                })
            if 'degreeProgram' in context:
                if not formatted_context["current_request"]["major"]:
                    formatted_context["current_request"]["major"] = context['degreeProgram'].get('major')

        print(f"Formatted context for prompty: {json.dumps(formatted_context, indent=2)}")

        # Generate queries using prompty
        raw_queries = prompty.execute(
            "information.prompty",
            inputs={
                "context": json.dumps(formatted_context),
                "chat_history": context.get("chat_history", []) if isinstance(context, dict) else [],
                "conversation_state": context.get("conversation_state", {}) if isinstance(context, dict) else {}
            }
        )

        # Parse and validate the generated queries
        if isinstance(raw_queries, str):
            try:
                queries_data = json.loads(raw_queries)
            except json.JSONDecodeError:
                queries_data = {
                    "queries": [],
                    "focus_areas": [],
                    "context": {},
                    "topic": "",
                    "error": "Failed to parse queries"
                }
        else:
            queries_data = raw_queries

        # Validate and correct queries
        expected_major = formatted_context["current_request"]["major"]
        if not expected_major:
            return {
                "courses": [],
                "requirements": [],
                "programs": [],
                "raw_results": {},
                "error": "No major specified in context"
            }

        queries_data = validate_queries(queries_data, expected_major)

        print(f"Validated queries: {json.dumps(queries_data, indent=2)}")

        # Continue with search process...
        search_client = AcademicInfoSearch()
        embedded_items = await search_client.get_embeddings(queries_data["queries"])
        if not embedded_items:
            return {
                "courses": [],
                "requirements": [],
                "programs": [],
                "raw_results": {},
                "error": "No embeddings generated"
            }

        results = await search_client.search_academic_info(embedded_items)

        processed_results = {
            "courses": [],
            "requirements": [],
            "programs": [],
            "raw_results": results
        }

        for query_results in results.values():
            for result in query_results:
                content_lower = result['content'].lower()
                if any(word in content_lower for word in ['course', 'prerequisite', 'sequence', 'credit']):
                    if result not in processed_results['courses']:
                        processed_results['courses'].append(result)
                if any(word in content_lower for word in ['requirement', 'required', 'curriculum', 'degree']):
                    if result not in processed_results['requirements']:
                        processed_results['requirements'].append(result)
                if any(word in content_lower for word in ['program', 'major', 'concentration', 'track']):
                    if result not in processed_results['programs']:
                        processed_results['programs'].append(result)

        return processed_results

    except Exception as e:
        logging.error(f"Error finding academic info: {e}")