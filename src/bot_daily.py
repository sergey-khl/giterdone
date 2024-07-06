import asyncio
import aiohttp
import logging
import os
import argparse

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import (
    OpenAILLMContext,
    LLMUserContextAggregator,
    LLMAssistantContextAggregator,
    OpenAILLMContextFrame,
    LLMUserResponseAggregator,
    LLMAssistantResponseAggregator,
)
from pipecat.processors.logger import FrameLogger
from pipecat.frames.frames import LLMMessagesFrame, EndFrame
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramTTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer
from loguru import logger
from prompts import *
from intake_processor import IntakeProcessor
from pipecat.pipeline.parallel_pipeline import ParallelPipeline
from pipecat.processors.filters.function_filter import FunctionFilter
from pipecat.processors.frame_processor import FrameDirection

from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(format=f"%(levelno)s %(asctime)s %(message)s")
logger = logging.getLogger("pipecat")
logger.setLevel(logging.DEBUG)

daily_api_key = os.getenv("DAILY_API_KEY", "")
daily_api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")

current_mode = "Default"


async def defaultFilter(frame) -> bool:
    return current_mode == "Default"


async def summarizerFilter(frame) -> bool:
    return current_mode == "Summarizer"


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
            ),
        )

        default_llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo"
        )

        summarizer_llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o"
        )

        messages = [BASE_PROMPT]
        context = OpenAILLMContext(messages=messages)
        user_context = LLMUserContextAggregator(context)
        assistant_context = LLMAssistantContextAggregator(context)

        fl = FrameLogger("LLM Output")

        # tma_in = LLMUserResponseAggregator(messages)
        # tma_out = LLMAssistantResponseAggregator(messages)

        tts = DeepgramTTSService(
            aiohttp_session=session,
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            voice="aura-helios-en",
        )

        pipeline = Pipeline(
            [
                transport.input(),
                # tma_in,
                user_context,
                # llm,
                ParallelPipeline(  # TTS (bot will speak the chosen language)
                    [FunctionFilter(defaultFilter), default_llm],  # English
                    [FunctionFilter(summarizerFilter), summarizer_llm],  # Spanish
                ),
                fl,
                tts,
                transport.output(),
                assistant_context,
                # tma_out
            ]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=False))

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            transport.capture_participant_transcription(participant["id"])
            # await task.queue_frames([LLMMessagesFrame(messages)])
            await task.queue_frames([OpenAILLMContextFrame(context)])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            global current_mode
            current_mode = "Summarizer"
            intake = IntakeProcessor(context, summarizer_llm)
            summarizer_llm.register_function("summarize", intake.summarize)
            await summarizer_llm.process_frame(
                OpenAILLMContextFrame(context), FrameDirection.DOWNSTREAM
            )
            await task.queue_frame(EndFrame())

        runner = PipelineRunner()

        await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipecat Simple ChatBot")
    parser.add_argument("-u", type=str, help="Room URL")
    parser.add_argument("-t", type=str, help="Token")
    config = parser.parse_args()

    asyncio.run(main(config.u, config.t))
