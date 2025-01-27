import logging
from typing import Dict, Any, List, Union, Tuple
from prompty.tracer import trace


# Import from shared types
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


class ConversationValidator:
    def __init__(self):
        self.intent_requirements = {
            "degree_planning": {
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
            },
            "course_scheduling": {
                "initial_query": {
                    "required": ["student_intent"],
                    "optional": ["current_courses"]
                },
                "gathering_info": {
                    "required": ["course_load", "semester"],
                    "optional": ["preferred_times"]
                },
                "needs_clarification": {
                    "required": ["scheduling_preferences"],
                    "optional": ["constraints"]
                }
            },
            "career_guidance": {
                "initial_query": {
                    "required": ["student_intent"],
                    "optional": ["major"]
                },
                "gathering_info": {
                    "required": ["career_goals"],
                    "optional": ["interests"]
                },
                "needs_clarification": {
                    "required": ["preferred_focus_areas"],
                    "optional": ["certifications"]
                }
            },
            "general_question": {
                "initial_query": {
                    "required": ["topic"],
                    "optional": []
                },
                "gathering_info": {
                    "required": ["specific_question"],
                    "optional": ["context"]
                }
            }
        }

        self.stage_transitions = {
            "degree_planning": {
                "initial_contact": ["degree_planning", "course_scheduling", "requirement_check"],
                "degree_planning": ["course_scheduling", "requirement_check"],
                "course_scheduling": ["review", "requirement_check"]
            },
            "course_scheduling": {
                "initial_query": ["gathering_info"],
                "gathering_info": ["needs_clarification", "ready_for_plan"],
                "needs_clarification": ["ready_for_plan"],
                "ready_for_plan": ["plan_created"]
            },
            "career_guidance": {
                "initial_query": ["gathering_info"],
                "gathering_info": ["needs_clarification", "ready_for_plan"],
                "needs_clarification": ["ready_for_plan"],
                "ready_for_plan": ["plan_created"]
            },
            "general_question": {
                "initial_query": ["gathering_info"],
                "gathering_info": ["needs_clarification", "ready_for_plan"],
                "needs_clarification": ["ready_for_plan"]
            }
        }

    async def validate_conversation_flow(
            self,
            validated_intent: ValidatedIntent,
            current_state: Dict[str, Any]
    ) -> ValidationResult:
        current_stage = current_state.get("current_stage", "initial_query")
        collected_info = current_state.get("collected_info", {})
        intent_type = validated_intent.type

        # Update collected info
        if validated_intent.data:
            collected_info.update({
                "major": validated_intent.data.get("major") or collected_info.get("major"),
                "degree_type": validated_intent.data.get("degree_type") or collected_info.get("degree_type"),
                "academic_year": "first_year" if ("first year" in str(validated_intent.data).lower() or
                                                  "freshman" in str(validated_intent.data).lower())
                else collected_info.get("academic_year"),
                "student_intent": collected_info.get("student_intent") or "degree_planning",
                "completed_courses": collected_info.get("completed_courses", []),
                "current_courses": collected_info.get("current_courses", [])
            })

        # Check what info is missing
        missing_info = []
        if intent_type in self.intent_requirements:
            if current_stage in self.intent_requirements[intent_type]:
                requirements = self.intent_requirements[intent_type][current_stage]
                for required_field in requirements["required"]:
                    if required_field not in collected_info:
                        missing_info.append({
                            "field": required_field,
                            "importance": "required"
                        })

        next_stage = self.determine_next_stage(intent_type, current_stage)
        is_valid_transition = next_stage in self.stage_transitions.get(intent_type, {}).get(current_stage, [])

        return ValidationResult(
            is_ready_to_proceed=len(missing_info) == 0 and is_valid_transition,
            current_stage=current_stage,
            missing_info=missing_info,
            next_action="gather_info" if missing_info else "proceed",
            suggested_prompt="",  # Remove suggested prompts
            state_valid=is_valid_transition,
            collected_info=collected_info,
            message=""  # Remove messages
        )

    def determine_next_stage(self, intent_type: str, current_stage: str) -> str:
        stage_mapping = {
            "degree_planning": {
                "initial_contact": "degree_planning",
                "degree_planning": "course_scheduling",
                "course_scheduling": "requirement_check"
            },
            "course_scheduling": {
                "initial_query": "gathering_info",
                "gathering_info": "needs_clarification",
                "needs_clarification": "ready_for_plan"
            },
            "career_guidance": {
                "initial_query": "gathering_info",
                "gathering_info": "needs_clarification",
                "needs_clarification": "ready_for_plan"
            },
            "general_question": {
                "initial_query": "gathering_info",
                "gathering_info": "ready_for_plan"
            }
        }
        return stage_mapping.get(intent_type, {}).get(current_stage, current_stage)


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