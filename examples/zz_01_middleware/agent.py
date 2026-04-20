import sys

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.panel import Panel

from middleware import AppendSystemPromptMiddleWare

# Load environment variables
load_dotenv()

console = Console()


def create_agent():
    model = ChatOpenAI(model="gpt-35-turbo", temperature=0)

    agent = create_deep_agent(
        model=model,  # Claude Sonnet 4.5 with temperature=0
        middleware=[AppendSystemPromptMiddleWare()],
    )
    return agent


def main():
    agent = create_agent()
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "brief introduction of yourself"}]}
        )

        # Extract and display the final answer
        final_message = result["messages"][-1]
        answer = (
            final_message.content
            if hasattr(final_message, "content")
            else str(final_message)
        )

        console.print(
            Panel(f"[bold green]Answer:[/bold green]\n\n{answer}", border_style="green")
        )

    except Exception as e:
        console.print(
            Panel(f"[bold red]Error:[/bold red]\n\n{str(e)}", border_style="red")
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
