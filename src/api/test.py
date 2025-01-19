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

    # Create a test intent with career guidance and external school comparison
    intent_data = {
        "type": "career_guidance",  # Changed to career_guidance to trigger research
        "data": {
            "major": "Computer Science",
            "degree_type": "BS",
            "interests": ["artificial intelligence"],
            "topics": ["career_path", "grad_school"],  # Added topics to trigger research
            "other_schools": ["Duke", "MIT", "Stanford"]
        }
    }

    # Create a test task with a question about career prospects and grad school
    task = ConversationTask(
        message="I'm interested in AI and machine learning. Can you compare the ML programs at Duke, MIT, and Stanford, and tell me about career prospects in this field? Don't worry about getting initial_contact information, I just want to know the difference between those schools, not interested in degree scheduling right now",
        intent=ValidatedIntent(**intent_data),
        conversation_state={
            "current_stage": "initial_contact",
            "collected_info": {
                "student_intent": "explore_careers",
                "major": "Computer Science",
                "degree_type": "BS",
                "career_interests": ["artificial intelligence", "machine learning"]
            }
        },
        context={
            "academic_year": "2024",
            "is_transfer": False,
            "research_needed": True,  # Flag indicating research is needed
            "research_topics": ["grad_school", "career_path", "other_universities"]
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
    # Environment check remains the same
    print("Environment check:")
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_KEY",
        "AZURE_SEARCH_INDEX_NAME"
    ]

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