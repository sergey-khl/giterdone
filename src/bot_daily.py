import asyncio
import aiohttp
import logging
import os
import argparse

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMAssistantResponseAggregator, LLMUserResponseAggregator
from pipecat.frames.frames import (
    LLMMessagesFrame,
    EndFrame
)
from pipecat.services.openai import OpenAILLMService
from pipecat.services.playht import PlayHTTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport 
from pipecat.vad.silero import SileroVADAnalyzer
from loguru import logger

from dotenv import load_dotenv
load_dotenv(override=True)

# logger.remove(0)
# logger.add(sys.stderr, level="DEBUG")
logging.basicConfig(format=f"%(levelno)s %(asctime)s %(message)s")
logger = logging.getLogger("pipecat")
logger.setLevel(logging.DEBUG)

daily_api_key = os.getenv("DAILY_API_KEY", "")
daily_api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")


async def main(room_url: str, token: str):
    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            room_url,
            token,
            "Chatbot",
            DailyParams(
                api_url=daily_api_url,
                api_key=daily_api_key,
                dialin_settings=None,
                audio_in_enabled=True,
                audio_out_enabled=True,
                camera_out_enabled=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=True,
            )
        )

        tts = PlayHTTTSService(
            user_id=os.getenv("PLAYHT_USER_ID"),
            api_key=os.getenv("PLAYHT_API_KEY"),
            voice_url="s3://voice-cloning-zero-shot/143f9a08-46a5-4d51-9d86-266d23d743c0/original/manifest.json",
        )

        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o")

        messages = [
            {
                "role": "system",
                "content": "You are a helpful LLM in a WebRTC call. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include special characters in your answers. Respond to what the user said in a creative and helpful way.",
            },
        ]

        tma_in = LLMUserResponseAggregator(messages)
        tma_out = LLMAssistantResponseAggregator(messages)

        pipeline = Pipeline([
            transport.input(),
            tma_in,
            llm,
            tts,
            transport.output(),
            tma_out,
        ])

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            transport.capture_participant_transcription(participant["id"])
            messages.append(
                {"role": "system", "content": "Please introduce yourself to the user."})
            await task.queue_frames([LLMMessagesFrame(messages)])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await task.queue_frame(EndFrame())

        @transport.event_handler("on_app_message")
        async def on_app_message(transport, message, sender):
            print(message, sender, messages)
            

        runner = PipelineRunner()

        await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipecat Simple ChatBot")
    parser.add_argument("-u", type=str, help="Room URL")
    parser.add_argument("-t", type=str, help="Token")
    config = parser.parse_args()

    asyncio.run(main(config.u, config.t))
