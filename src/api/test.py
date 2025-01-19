import asyncio
import json
import os
from dotenv import load_dotenv

# Import from shared types
from src.api.type_def import ValidatedIntent, ConversationTask
from src.api.orchestrator import orchestrate_conversation

load_dotenv()


async def test_advisor():
    print("Starting advisor test...")

    # Create a test intent
    intent_data = {
        "type": "degree_planning",
        "data": {
            "major": "Computer Science",
            "degree_type": "BS",
            "interests": ["artificial intelligence"]
        }
    }

    # Create a test task
    task = ConversationTask(
        message="I want to major in Computer Science and I'm interested in AI.",
        intent=ValidatedIntent(**intent_data),
        conversation_state={
            "current_stage": "initial_contact",
            "collected_info": {
                "student_intent": "explore_majors",
                "major": "Computer Science",
                "degree_type": "BS"
            }
        },
        context={
            "academic_year": "2024",
            "is_transfer": False
        }
    )

    try:
        print("\nSending request to advisor...")

        async for message in orchestrate_conversation(task):
            result = json.loads(message)
            print(f"\nMessage Type: {result['type']}")
            print(f"Message: {result['message']}")
            if result.get('data'):
                print("Data:")
                print(json.dumps(result['data'], indent=2))
            print("-" * 50)

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"\nError during test: {str(e)}")
        raise


if __name__ == "__main__":
    print("Environment check:")
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_KEY",
        "AZURE_SEARCH_INDEX_NAME"
    ]

    # Check environment variables
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        exit(1)

    print("All required environment variables are set!")

    # Run the test
    asyncio.run(test_advisor())