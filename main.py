"""
Main entry point for Osaka CLI
"""

import sys
import argparse
from osaka import AIAgent
from osaka.config import setup_logging, load_environment, get_api_key


def main():
    """Main CLI function"""
    # Setup
    load_environment()
    setup_logging()
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Osaka - A conversational AI agent with file editing capabilities"
    )
    parser.add_argument(
        "--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)"
    )
    args = parser.parse_args()

    # Get API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print(
            "Error: Please provide an API key via --api-key or ANTHROPIC_API_KEY environment variable"
        )
        sys.exit(1)

    # Initialize agent
    agent = AIAgent(api_key)

    # Print welcome message
    print("Osaka")
    print("=================")
    print("A conversational AI agent that can read, list, and edit files.")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("Type 'undo' to revert the last file change.")
    print()

    # Main conversation loop
    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("\nAssistant: ", end="", flush=True)
            response = agent.chat(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print()


if __name__ == "__main__":
    main()