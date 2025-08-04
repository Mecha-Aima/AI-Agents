from workflow import create_workflow
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

thread_count = 1

def main():
    workflow = create_workflow()
    print("="*50)
    print("Welcome to the Social Media Manager")
    print("="*50)
    name = input("Enter your name: ")
    print("-"*50)
    print("Type 'exit' to end the conversation. 'new' to start a new chat." )

    config = {'configurable': {'user_id': name, 'thread_id': thread_count}}

    while True:
        user_input = input("\n👤 You: ")
        if user_input.lower() == "exit":
            print("Exiting...")
            break 
        elif user_input.lower() == "new":
            config["configurable"]['thread_id'] += 1
            print("-"*50)
            print(f"New chat started. Thread ID: {config['configurable']['thread_id']}")
            print("-"*50)

        input_message = [HumanMessage(content=user_input)]

        for chunk in workflow.stream({'messages':input_message}, config=config, stream_mode="values"):
            if isinstance(chunk["messages"][-1], AIMessage) or isinstance(chunk["messages"][-1], ToolMessage):
                chunk["messages"][-1].pretty_print()

if __name__ == "__main__":
    main()