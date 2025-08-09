from dataclasses import dataclass
from langgraph.graph import StateGraph 
from gmail_assistant.tools.run_ingest import fetch_and_process_emails

@dataclass(kw_only=True)
class JobKickoff:
    email: str 
    minutes_since: int = 30 
    graph_name: str = "gmail_assistant"
    url: str = "http://127.0.0.1:2024"
    include_read: bool = False 
    rerun: bool = False 
    early: bool = False 
    skip_filters: bool = False 


async def main(state: JobKickoff):
    """Run the email ingestion process"""
    print(f"Kicking off job to fetch emails from the past {state.minutes_since} minutes")
    print(f"Email: {state.email}")
    print(f"URL: {state.url}")
    print(f"Graph name: {state.graph_name}")
    
    try:
        class Args:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
                print(f"Created Args with attributes: {dir(self)}")

        args = Args(
            email=state.email,
            minutes_since=state.minutes_since,
            graph_name=state.graph_name,
            url=state.url,
            include_read=state.include_read,
            rerun=state.rerun,
            early=state.early,
            skip_filters=state.skip_filters
        )

        print(f"Args email: {args.email}")
        print(f"Args url: {args.url}")

        print("🟩 Starting fetch_and_process_emails...")
        result = await fetch_and_process_emails(args)
        print(f"🟨 fetch_and_process_emails returned: {result}")

        return {"status": "success" if result == 0 else "error", "exit_code": result}

    except Exception as e:
        import traceback
        print(f"‼️ Error in cron job: {str(e)}")
        print(traceback.format_exc())
        return {"status": "error", "error": str(e)}
    
graph = StateGraph(JobKickoff)
graph.add_node("ingest_emails", main)
graph.set_entry_point("ingest_emails")
graph = graph.compile()