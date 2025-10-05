#!/usr/bin/env python3
"""FastAPI service for IDE agent with CopilotKit integration."""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

load_dotenv()

from fastapi import FastAPI
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from web_agent.agent import create_custom_agent
from web_agent.config import settings

db_url = settings.postgres_dsn

langfuse = Langfuse(
    public_key=settings.langfuse_public_key.get_secret_value(),
    secret_key=settings.langfuse_secret_key.get_secret_value(),
    host=settings.langfuse_host,
)

langfuse_handler = CallbackHandler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncConnectionPool(
        db_url, open=False, kwargs=dict(autocommit=True)
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        graph = create_custom_agent(checkpointer)

        sdk = CopilotKitRemoteEndpoint(
            agents=[
                LangGraphAGUIAgent(
                    name="ide_agent",
                    description="Software engineering IDE assistant with file editing and bash capabilities",
                    graph=graph,
                    config={
                        "configurable": {"thread_id": "custom-test-123"},
                        "recursion_limit": 200,
                        "callbacks": [langfuse_handler],
                    },
                ),
            ],
        )

        add_fastapi_endpoint(app, sdk, "/copilotkit")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "trae-web-ide-agent"}


@app.get("/")
def root():
    """Root endpoint with service information."""
    return {
        "service": "trae-web-ide-agent",
        "description": "LangGraph IDE agent with trae-agent tools converted to LangChain",
        "endpoints": {"copilotkit": "/copilotkit", "health": "/health"},
    }


def main():
    """Run the FastAPI server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
