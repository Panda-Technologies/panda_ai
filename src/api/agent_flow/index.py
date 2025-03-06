import os
import asyncio
from dotenv import load_dotenv

from src.api.agent_flow.chat_flow.ConversationStateManager import ConversationStateManager


async def chat():
    load_dotenv()
    # Initialize the client.
    client = ConversationStateManager(
        azure_openai_deployment=os.environ["AZURE_DEPLOYMENT_NAME"],
        azure_openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )

    print("Welcome to the Intelligent RAG Chat Client!")
    print("Type 'exit' to end the conversation.\n")

    while True:
        try:
            user_input = input("User> ")
            if user_input.lower() == "exit":
                print("\nGoodbye!")
                break

            response = await client.process_message(str(user_input))

            print("\nAssistant> ", end="")
            print(response)

            print()

        except KeyboardInterrupt:
            print("\n\nExiting chat...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            continue


if __name__ == "__main__":
    asyncio.run(chat())
