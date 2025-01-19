import os
import json
import traceback
from typing import List, Dict, Optional
import requests
from dotenv import load_dotenv
import prompty
from prompty.azure.processor import ToolCall
from prompty.tracer import trace

load_dotenv()


class AcademicResearcher:
    def __init__(self):
        self.bing_endpoint = os.getenv("BING_SEARCH_ENDPOINT")
        self.bing_key = os.getenv("BING_SEARCH_KEY")
        self.headers = {"Ocp-Apim-Subscription-Key": self.bing_key}

        # Keywords that indicate external research is needed
        self.external_triggers = {
            "other_schools": [
                "other university", "other college", "different school",
                "transfer", "duke", "nc state", "medical school"
            ],
            "careers": [
                "job market", "career", "industry", "profession",
                "salary", "employment", "job outlook"
            ],
            "grad_school": [
                "graduate school", "grad school", "mcat", "gre", "lsat",
                "medical school", "law school", "phd", "masters"
            ],
            "professional": [
                "internship", "certification", "professional development",
                "summer program", "research opportunity"
            ]
        }

    def _make_request(self, path: str, params: Dict) -> Dict:
        """Make a request to Bing API"""
        endpoint = f"{self.bing_endpoint.rstrip('/')}/{path}"
        response = requests.get(endpoint, headers=self.headers, params=params)
        return response.json()

    @trace
    def needs_research(self, query: str) -> Optional[List[str]]:
        """Determine if query needs external research and in what categories"""
        query_lower = query
        needed_categories = []

        for category, triggers in self.external_triggers.items():
            if any(trigger in query_lower for trigger in triggers):
                needed_categories.append(category)

        return needed_categories if needed_categories else None

    @trace
    async def find_information(self, query: str, market: str = "en-US") -> Dict:
        """Enhanced web search focusing on educational and professional sources"""
        params = {
            "q": query,
            "mkt": market,
            "count": 5,
            "responseFilter": "Webpages",
            "freshness": "Month"  # Prefer recent results
        }

        items = self._make_request("v7.0/search", params)

        if "webPages" not in items:
            return {"pages": [], "related": []}

        # Filter for educational and professional domains
        edu_domains = [".edu", ".org", ".gov"]
        pages = [
            {
                "url": page["url"],
                "name": page["name"],
                "description": page["snippet"]
            }
            for page in items["webPages"]["value"]
            if any(domain in page["url"].lower() for domain in edu_domains)
        ]

        related = items.get("relatedSearches", {}).get("value", [])
        return {
            "pages": pages[:5],
            "related": [r["text"] for r in related]
        }

    @trace
    async def research_topic(self,
                             instruction: str,
                             current_state: Optional[Dict] = None,
                             feedback: str = "No feedback") -> Dict:
        """Main research function that determines need and executes research"""
        try:
            categories = self.needs_research(instruction)
            if not categories:
                return {
                    "needed": False,
                    "message": "No external research needed - UNC-specific query"
                }

            print(f"Research categories found: {categories}")

            research_calls: List[ToolCall] = prompty.execute(
                "researcher.prompty",
                inputs={
                    "instructions": instruction,
                    "feedback": feedback,
                    "categories": categories
                }
            )

            print(f"Research calls received: {research_calls}")

            # Execute research
            results = []
            for call in research_calls:
                print(f"Processing call: {call.name}")
                args = json.loads(call.arguments)
                print(f"With arguments: {args}")

                if call.name in ["find_information", "find_academic_info", "find_career_info",
                                 "find_research_opportunities", "find_grad_school_info"]:
                    # Use the base find_information method for all search types
                    search_query = args.get("query", "")
                    if not search_query:
                        continue

                    result = await self.find_information(
                        query=search_query,
                        market=args.get("market", "en-US")
                    )

                    results.append({
                        "type": call.name,  # Keep track of what type of search this was
                        "query": search_query,
                        "category": args.get("category") or args.get("focus") or args.get("program_type"),
                        "data": result
                    })
                    print(f"Got result: {result}")

            return {
                "needed": True,
                "categories": categories,
                "results": results
            }

        except Exception as e:
            print(f"Error in research: {e}")
            traceback.print_exc()  # Add this for better error tracking
            return {
                "needed": False,
                "error": str(e),
                "message": "Error during research process"
            }

@trace
async def process_results(results: Dict) -> Dict:
    """Process and structure research results"""
    if not results.get("needed", False):
        return results

    processed = {
        "categories": results["categories"],
        "information": []
    }

    for result in results.get("results", []):
        if result["type"] == "information":
            for page in result["data"].get("pages", []):
                info = {
                    "source": page["name"],
                    "url": page["url"],
                    "content": page["description"]
                }
                processed["information"].append(info)

    return processed


if __name__ == "__main__":
    import asyncio


    async def test():
        researcher = AcademicResearcher()
        instruction = "What are the prerequisites for Duke medical school?"
        results = await researcher.research_topic(instruction)
        processed = await process_results(results)
        print(json.dumps(processed, indent=2))


    asyncio.run(test())