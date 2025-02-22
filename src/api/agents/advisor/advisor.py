import json
from typing import Dict, Any, Optional
import prompty
from prompty.tracer import trace
from dotenv import load_dotenv
import logging

from src.api.agents.information.information import AcademicInfoSearch, find_academic_info
from src.api.agents.researcher.researcher import AcademicResearcher

load_dotenv()


class AdvisorState:
    """Tracks the state of the advising conversation"""

    def __init__(self):
        self.stages = {
            "initial_contact": ["student_intent", "academic_standing"],
            "major_selection": ["intended_major", "degree_type", "interests"],
            "course_history": ["completed_courses", "transfer_credits", "current_courses"],
            "requirement_check": ["major_requirements", "gen_ed_requirements"],
            "schedule_planning": ["target_graduation", "course_load", "preferences"],
            "career_planning": ["career_goals", "grad_school_plans", "certifications"]
        }

        self.required_fields = {
            "degree_planning": ["major", "academic_year", "completed_courses"],
            "career_guidance": ["interests", "career_goals"],
            "academic_support": ["current_courses", "academic_standing"],
            "general_questions": ["topic"]
        }


@trace
async def advise(
        conversation_context: str,
        research_context: Optional[str],
        academic_context: str,
        current_state: Dict[str, Any],
        feedback: str = "No Feedback"
) -> Dict[str, Any]:
    """
    Main advising function that generates responses based on context and state
    """
    try:
        # Extract chat history from current state
        chat_history = current_state.get("chat_history", [])

        # Format chat history for the prompt
        formatted_history = []
        for msg in chat_history:
            role = msg.get("role", "unknown")
            content = msg.get("message", "")
            formatted_history.append(f"{role}: {content}")

        # Get research if needed
        research_results = {}
        if research_context:
            researcher = AcademicResearcher()
            research_results = await researcher.research_topic(research_context)
            print(f'Research results: {research_results}')

        # Generate advisor response with chat history
        response = prompty.execute(
            "advisor.prompty",
            parameters={"stream": True},
            inputs={
                "researchContext": research_context,
                "research": research_results,
                "academicInfo": academic_context or {},
                "currentState": current_state,
                "chatHistory": formatted_history,
                "feedback": feedback,
                "assignment": conversation_context
            }
        )

        return response

    except Exception as e:
        logging.error(f"Error in advising: {e}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "fallback_response": "I apologize...",
            "stage": current_state.get("current_stage", "unknown")
        }


@trace
def process_response(response: str) -> Dict[str, Any]:
    """Process the advisor's response and extract any feedback"""
    if "---" in response:
        parts = response.split("---")
        return {
            "response": parts[0].strip(),
            "feedback": parts[1].strip() if len(parts) > 1 else None
        }
    return {
        "response": response.strip(),
        "feedback": None
    }


if __name__ == "__main__":
    import asyncio


    async def test():
        # Test conversation
        conversation = {
            "context": "I'm interested in majoring in Computer Science but also considering pre-med. Can you help me plan my courses?",
            "current_state": {
                "stage": "initial_contact",
                "collected_info": {
                    "student_intent": "degree_planning",
                    "interests": ["computer_science", "pre_med"]
                }
            }
        }

        research_context = "What are typical prerequisites for medical school admission?"
        academic_context = "Computer Science BS requirements and pre-med track courses"

        result = await advise(
            conversation["context"],
            research_context,


            academic_context,
            conversation["current_state"]
        )

        processed = process_response(result)
        print(json.dumps(processed, indent=2))


    asyncio.run(test())