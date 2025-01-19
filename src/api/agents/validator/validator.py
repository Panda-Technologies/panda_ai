import logging
from typing import Dict, Any, List, Union, Tuple
from prompty.tracer import trace


# Import from shared types
from src.api.type_def import ValidatedIntent, ValidationResult

class ConversationValidator:
    def __init__(self):
        # Define required information for each stage
        self.stage_requirements = {
            "initial_contact": {
                "required": ["student_intent"],
                "optional": ["academic_year", "transfer_credits"]
            },
            "degree_planning": {
                "required": ["major", "degree_type"],
                "optional": ["interests", "career_goals"]
            },
            "course_scheduling": {
                "required": ["semester", "completed_courses"],
                "optional": ["preferred_times", "course_load"]
            }
        }

        # Define valid stage transitions
        self.valid_transitions = {
            "initial_contact": ["degree_planning", "course_scheduling", "general_info"],
            "degree_planning": ["course_scheduling", "requirement_check"],
            "course_scheduling": ["review", "requirement_check"]
        }

    async def validate_conversation_flow(
            self,
            validated_intent: ValidatedIntent,
            current_state: Dict[str, Any]
    ) -> ValidationResult:
        try:
            current_stage = current_state.get("current_stage", "initial_contact")
            collected_info = current_state.get("collected_info", {})
            intent_type = validated_intent.type

            # Check if we have all required info for current stage
            missing_info = []
            if current_stage in self.stage_requirements:
                for required_field in self.stage_requirements[current_stage]["required"]:
                    if required_field not in collected_info:
                        missing_info.append({
                            "field": required_field,
                            "importance": "required"
                        })

            # Determine if the intended transition is valid
            next_stage = self.determine_next_stage(intent_type, current_stage)
            is_valid_transition = next_stage in self.valid_transitions.get(current_stage, [])

            # Generate appropriate next action/prompt
            next_action, suggested_prompt = self.generate_next_step(
                current_stage,
                missing_info,
                validated_intent,
                is_valid_transition
            )

            return ValidationResult(
                is_ready_to_proceed=len(missing_info) == 0 and is_valid_transition,
                current_stage=current_stage,
                missing_info=missing_info,
                next_action=next_action,
                suggested_prompt=suggested_prompt or "",  # Provide default empty string
                state_valid=is_valid_transition
            )
        except Exception as e:
            logging.error(f"Error in validation: {e}", exc_info=True)
            return ValidationResult(
                is_ready_to_proceed=False,
                current_stage=current_stage,
                missing_info=[],
                next_action="error",
                suggested_prompt="I apologize, but I encountered an error validating the conversation state.",
                state_valid=False
            )

    def determine_next_stage(self, intent_type: str, current_stage: str) -> str:
        """Maps intent types to next stages"""
        stage_mapping = {
            "degree_planning": "degree_planning",
            "course_scheduling": "course_scheduling",
            "general_question": "general_info"
        }
        return stage_mapping.get(intent_type, current_stage)

    def generate_next_step(
            self,
            current_stage: str,
            missing_info: List[Dict[str, str]],
            intent: ValidatedIntent,
            is_valid_transition: bool
    ) -> Tuple[str, str]:
        """Generates next action and suggested prompt based on validation results"""
        if not is_valid_transition:
            return (
                "redirect",
                f"I notice you want to discuss {intent.type}. "
                f"However, let's first complete your {current_stage} information."
            )

        if missing_info:
            field = missing_info[0]["field"]
            return (
                "gather_info",
                f"Could you tell me your {field.replace('_', ' ')}?"
            )

        return (
            "proceed",
            "Great! Let's continue with your request."  # Default message instead of None
        )


@trace
async def validate_state(intent: ValidatedIntent, state: Dict[str, Any]) -> Dict[str, Any]:
    """Main validation function called by orchestrator"""
    validator = ConversationValidator()
    result = await validator.validate_conversation_flow(intent, state)
    return result.model_dump()


if __name__ == "__main__":
    # Test the validator
    test_intent = {
        "type": "degree_planning",
        "data": {
            "major": "Computer Science"
        }
    }
    test_state = {
        "current_stage": "initial_contact",
        "collected_info": {
            "student_intent": "explore_majors"
        }
    }

    import asyncio

    result = asyncio.run(validate_state(test_intent, test_state))
    print(result)