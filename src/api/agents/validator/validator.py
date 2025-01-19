import logging
from typing import Dict, Any, List, Union, Tuple
from prompty.tracer import trace


# Import from shared types
from src.api.type_def import ValidatedIntent, ValidationResult

class ConversationValidator:
    def __init__(self):
        # Define required information only for degree planning
        self.degree_planning_requirements = {
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

        # Define valid stage transitions for degree planning
        self.degree_planning_transitions = {
            "initial_contact": ["degree_planning", "course_scheduling", "requirement_check"],
            "degree_planning": ["course_scheduling", "requirement_check"],
            "course_scheduling": ["review", "requirement_check"]
        }

    async def validate_conversation_flow(
            self,
            validated_intent: ValidatedIntent,
            current_state: Dict[str, Any]
    ) -> ValidationResult:
        """Validates conversation flow based on intent"""
        current_stage = current_state.get("current_stage", "initial_contact")
        collected_info = current_state.get("collected_info", {})
        intent_type = validated_intent.type

        # Only check for missing information if this is a degree planning intent
        missing_info = []
        is_valid_transition = True
        next_action = "proceed"
        suggested_prompt = None

        if intent_type == "degree_planning":
            # Check required info for current stage
            if current_stage in self.degree_planning_requirements:
                for required_field in self.degree_planning_requirements[current_stage]["required"]:
                    if required_field not in collected_info:
                        missing_info.append({
                            "field": required_field,
                            "importance": "required"
                        })

            # Check stage transition for degree planning
            next_stage = self.determine_next_stage(intent_type, current_stage)
            is_valid_transition = next_stage in self.degree_planning_transitions.get(current_stage, [])

            # Generate next step only for degree planning
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
            suggested_prompt=suggested_prompt or "",
            state_valid=is_valid_transition
        )

    def determine_next_stage(self, intent_type: str, current_stage: str) -> str:
        """Maps intent types to next stages"""
        if intent_type == "degree_planning":
            stage_mapping = {
                "degree_planning": "degree_planning",
                "course_scheduling": "course_scheduling",
                "requirement_check": "requirement_check"
            }
            return stage_mapping.get(intent_type, current_stage)
        return current_stage

    def generate_next_step(
            self,
            current_stage: str,
            missing_info: List[Dict[str, str]],
            intent: ValidatedIntent,
            is_valid_transition: bool
    ) -> Tuple[str, str]:
        """Generates next action and prompt only for degree planning"""
        if not is_valid_transition:
            return (
                "redirect",
                f"I notice you want to discuss degree planning. "
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
            "Great! Let's continue with your request."
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