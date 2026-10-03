import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.common.client import AegisMeshClient
from agents.researcher.agent import ResearcherAgent


async def run_search(query: str) -> None:
    client = AegisMeshClient(
        base_url=os.getenv("AEGISMESH_URL", "http://127.0.0.1:8000")
    )
    agent = ResearcherAgent(client=client)
    mission_id = f"mission-{uuid.uuid4().hex[:8]}"
    session_id = f"session-{uuid.uuid4().hex[:8]}"

    result = await agent.execute_web_search(
        query=query,
        mission_id=mission_id,
        session_id=session_id,
    )
    print(
        json.dumps(
            {
                "mission_id": mission_id,
                "session_id": session_id,
                "decision": agent.last_decision.model_dump(mode="json"),
                "result": result,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a guarded AegisMesh agent search.")
    parser.add_argument("query", help="Search query to submit through the agent")
    args = parser.parse_args()
    asyncio.run(run_search(args.query))


if __name__ == "__main__":
    main()