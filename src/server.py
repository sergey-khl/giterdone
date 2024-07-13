"""
server.py

create callbots, remove view status

"""

import os
import argparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import bots

from dotenv import load_dotenv

load_dotenv(override=True)

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "DAILY_API_KEY",
    "DEEPGRAM_API_KEY",
    "DAILY_API_URL",
    "AWS_REGION"
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bots.router, prefix="/bots", tags=["bots"])

if __name__ == "__main__":
    # Check environment variables
    for env_var in REQUIRED_ENV_VARS:
        if env_var not in os.environ:
            raise Exception(f"Missing environment variable: {env_var}.")

    parser = argparse.ArgumentParser(description="giterdone server")
    parser.add_argument(
        "--host", type=str, default=os.getenv("HOST", "0.0.0.0"), help="Host address"
    )
    parser.add_argument(
        "--port", type=int, default=os.getenv("PORT", 7860), help="Port number"
    )
    parser.add_argument(
        "--reload", action="store_true", default=True, help="Reload code on change"
    )

    config = parser.parse_args()

    try:
        import uvicorn

        uvicorn.run(
            "server:app", host=config.host, port=config.port, reload=config.reload
        )

    except KeyboardInterrupt:
        print("runner shutting down...")
