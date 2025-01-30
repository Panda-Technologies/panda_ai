import json
import logging
from typing import Dict, Any, List, Tuple
import prompty
from prompty.tracer import trace
from src.api.type_def import ValidatedIntent, ValidationResult

def generate_next_step(
        current_stage: str,
        missing_info: List[Dict[str, str]],
        intent: ValidatedIntent,
        is_valid_transition: bool
) -> Tuple[str, str]:
    """Generates next action and prompt based on conversation state"""
    if not is_valid_transition:
        return (
            "redirect",
            f"Let's complete your {current_stage} information before moving forward."
        )

    if missing_info:
        field = missing_info[0]["field"]
        prompts = {
            "student_intent": "What would you like help with today?",
            "major": "What major are you interested in?",
            "degree_type": "Are you pursuing a BA or BS degree?",
            "career_goals": "What are your career goals?",
            "course_load": "How many courses would you like to take per semester?",
            "scheduling_preferences": "Do you prefer morning, afternoon, or evening classes?",
            "topic": "What specific topic would you like to know more about?",
            "specific_question": "Could you clarify your question?",
        }
        return ("gather_info", prompts.get(field, f"Could you tell me your {field.replace('_', ' ')}?"))

    return ("proceed", "Great! Let's continue.")

@trace
async def validate_state(intent: ValidatedIntent, state: Dict[str, Any], message: str = "") -> Dict[str, Any]:
    """Main validation function with AI-determined academic info checking"""
    relevant_state = {
        "current_stage": state.get("current_stage"),
        "collected_info": state.get("collected_info", {}),
        # Include only last few relevant messages
        "recent_messages": state.get("chat_history", [])[-3:] if state.get("chat_history") else []
    }
    print("Relevant State: ", relevant_state)
    try:
        # Execute the validator prompt
        raw_validation_result = prompty.execute(
            "validator.prompty",
            inputs={
                "conversation": message,
                "current_state": json.dumps(relevant_state),
                "intent": json.dumps(intent.model_dump())
            }
        )
        # Parse the JSON response
        try:
            validation_result = json.loads(raw_validation_result) if isinstance(raw_validation_result, str) else raw_validation_result
        except json.JSONDecodeError as je:
            logging.error(f"Failed to parse validation result: {je}")
            return {
                "is_ready_to_proceed": False,
                "current_stage": state.get("current_stage", "initial_query"),
                "missing_info": [],
                "next_action": "error",
                "state_valid": False,
                "collected_info": state.get("collected_info", {}),
                "needs_academic_info": False,
                "academic_info_reason": "Error parsing validation result",
                "message": str(je)
            }

        # Ensure we have all required fields
        return {
            "is_ready_to_proceed": validation_result.get("isValid", False),
            "current_stage": validation_result.get("currentStage", state.get("current_stage", "initial_query")),
            "missing_info": validation_result.get("missingInformation", []),
            "next_action": "proceed",
            "state_valid": True,
            "collected_info": state.get("collected_info", {}),
            "needs_academic_info": validation_result.get("needsAcademicInfo", False),
            "academic_info_reason": validation_result.get("reasonForAcademicInfo", ""),
            "message": ""
        }

    except Exception as e:
        logging.error(f"Error in validation: {str(e)}")
        return {
            "is_ready_to_proceed": False,
            "current_stage": state.get("current_stage", "initial_query"),
            "missing_info": [],
            "next_action": "error",
            "state_valid": False,
            "collected_info": state.get("collected_info", {}),
            "needs_academic_info": False,
            "academic_info_reason": "Error in validation",
            "message": str(e)
        }

if __name__ == "__main__":
    test_intent = ValidatedIntent(
        type="degree_planning",
        data={"major": "Computer Science"}
    )
    test_state = {
        "current_stage": "initial_contact",
        "collected_info": {
            "student_intent": "explore_majors"
        }
    }

    import asyncio
    result = asyncio.run(validate_state(test_intent, test_state))
    print(result)