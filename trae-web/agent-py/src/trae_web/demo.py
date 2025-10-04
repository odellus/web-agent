#!/usr/bin/env python3
"""FastAPI service for IDE agent with CopilotKit integration."""

import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent

from trae_web.agent import create_ide_agent

app = FastAPI()
sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="ide_agent",
            description="Software engineering IDE assistant with file editing and bash capabilities",
            graph=create_ide_agent(),
            config={
                "configurable": {
                    # Add any configurable parameters needed for your agent
                }
            },
        ),
    ],
)

add_fastapi_endpoint(app, sdk, "/copilotkit")


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
