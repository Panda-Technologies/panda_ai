from __future__ import annotations

from typing import List, Union, Dict, AsyncGenerator, Any
from prompty.tracer import trace
import logging
import json

# Import from shared types
from src.api.type_def import ConversationTask, Message, ValidatedIntent, TypeChatContext, ConversationState

# Import agents
from src.api.agents.researcher.researcher import AcademicResearcher
from src.api.agents.information.information import find_academic_info
from src.api.agents.advisor.advisor import advise
from src.api.agents.validator.validator import validate_state

def create_message(type: str, message: str, data: Union[Dict, List] = None) -> str:
    """Create a standardized message"""
    return Message(
        type=type,
        message=message,
        data=data or {}
    ).to_json_line()

@trace
async def should_research(intent: ConversationTask) -> bool:
    """Determine if external research is needed based on intent"""
    research_requiring_intents = {
        "career_guidance": True,
        "degree_planning": ["grad_school", "career_path", "other_universities"],
    }

    needs_research = research_requiring_intents.get(intent.type, False)
    if isinstance(needs_research, list):
        return any(topic in intent.data.get("topics", []) for topic in needs_research)
    return needs_research


async def process_typechat_context(context: TypeChatContext, state: ConversationState) -> Dict[str, Any]:
    """Process TypeChat context to enhance AI understanding"""

    # Map TypeChat categories to AI advisor stages
    stage_mapping = {
        "initial_query": "gathering_info",
        "gathering_info": "needs_clarification",
        "needs_clarification": "ready_for_plan",
        "ready_for_plan": "plan_created"
    }

    # Update state with TypeChat information
    current_stage = state.current_stage
    if context.data and context.data.get("context"):
        current_stage = context.data["context"].get("currentStage", current_stage)

    # Enhance collected info with TypeChat data
    collected_info = state.collected_info or {}
    if context.data:
        if initial_info := context.data.get("initialInfo"):
            collected_info.update({
                "major": initial_info.get("major"),
                "degree_type": initial_info.get("degreeType"),
                "start_term": initial_info.get("startTerm")
            })

        if preferences := context.data.get("courseFocusPreferences"):
            collected_info.update({
                "interests": preferences.get("preferredGenEdFocuses", {}).get("focusAreas"),
                "career_goals": preferences.get("careerGoal", {}).get("futureJobInterest")
            })

    return {
        "current_stage": stage_mapping.get(current_stage, current_stage),
        "collected_info": {k: v for k, v in collected_info.items() if v is not None}
    }

@trace
async def orchestrate_conversation(task: ConversationTask) -> AsyncGenerator[str, None]:
    try:
        # 1. Validate conversation state and flow
        yield create_message("state_validation", "Validating conversation flow...")

        # Convert dictionary to object attributes if needed
        if isinstance(task.conversation_state, dict):
            state = {
                "current_stage": task.conversation_state.get("current_stage") or
                                 task.conversation_state.get("stage") or
                                 "initial_query",
                "collected_info": task.conversation_state.get("collected_info") or
                                  task.conversation_state.get("info", {}),
                "typechat_history": task.conversation_state.get("typechat_history") or
                                    task.conversation_state.get("history", [])
            }
            task.conversation_state = state

        flow_validation = await validate_state(task.intent, task.conversation_state)

        # 2. Check if external research is needed
        research_results = None
        if await should_research(task.intent):
            researcher = AcademicResearcher()
            yield create_message("researcher", "Gathering external information...")
            research_results = await researcher.research_topic(
                instruction=task.message,
                current_state=task.conversation_state  # Now matches the parameter
            )
            yield create_message("researcher", "Research complete", research_results)

        # 3. Get relevant academic information
        yield create_message("academic_info", "Retrieving academic information...")
        print(f"Academic context2: {task.intent.data}")
        academic_results = await find_academic_info(
            context=task.intent.data
        )
        print(f"Academic results: {academic_results}")
        yield create_message("academic_info", "Academic info retrieved", academic_results)

        # 4. Generate advisor response
        yield create_message("advisor", "Generating response...", {"start": True})

        # Update conversation state with new information
        updated_state = task.conversation_state.copy()
        updated_state["collected_info"] = {
            **task.conversation_state.get("collected_info", {}),
            **flow_validation.get("collected_info", {})
        }
        updated_state["current_stage"] = flow_validation.get("current_stage", updated_state.get("current_stage"))
        updated_state["validation_result"] = flow_validation
        updated_state["last_intent"] = task.intent.model_dump()
        print(f"Updated state: {academic_results}")

        advisor_response = await advise(
            conversation_context=task.message,
            research_context=research_results,
            academic_context=academic_results,
            current_state=updated_state
        )

        # 5. Stream the response
        if isinstance(advisor_response, str):
            yield create_message("partial", "Response", {"text": advisor_response})
        else:
            for chunk in advisor_response:
                yield create_message("partial", "Response chunk", {"text": chunk})

        # 6. Final state validation
        yield create_message("advisor", "Response complete", {"complete": True})

        # 7. Update and return final state
        final_state = {
            "stage_complete": flow_validation["is_ready_to_proceed"],
            "next_stage": flow_validation.get("next_stage"),
            "collected_info": updated_state.get("collected_info", {}),
            "current_stage": flow_validation["current_stage"]
        }
        yield create_message("state_validation", "Final state", final_state)

    except Exception as e:
        error_msg = f"Error in conversation: {str(e)}"
        logging.error(error_msg)
        yield create_message(
            "error",
            f"Error in conversation: {str(e)}",
            {"type": "orchestration_error", "details": str(e)}
        )


if __name__ == "__main__":
    import asyncio


    async def test():
        # Test with a pre-validated intent (as if from TypeChat)
        task = ConversationTask(
            message="I want to major in Computer Science",
            intent=ValidatedIntent(
                type="degree_planning",
                data={
                    "major": "Computer Science",
                    "degree_type": None,
                    "interests": []
                }
            ),
            conversation_state={
                "current_stage": "initial_contact",
                "collected_info": {
                    "student_intent": "explore_majors"
                }
            }
        )

        async for message in orchestrate_conversation(task):
            result = json.loads(message)
            print(f"{result['type']}: {result['message']}")
            if result['data']:
                print(json.dumps(result['data'], indent=2))
            print("---")


    asyncio.run(test())