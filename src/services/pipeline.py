import argparse
import asyncio
import logging
import os

import aiohttp
from custom_pipeline_runner import CustomPipelineRunner, summarize
from dotenv import load_dotenv
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantContextAggregator,
    LLMUserContextAggregator,
    OpenAILLMContext,
    OpenAILLMContextFrame,
)
from pipecat.processors.logger import FrameLogger
from pipecat.services.deepgram import DeepgramTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import (
    DailyParams,
    DailyTransport,
)
from pipecat.vad.silero import SileroVADAnalyzer
from prompts import BASE_PROMPT
from twilio.rest import Client

load_dotenv(override=True)

logging.basicConfig(format="%(levelno)s %(asctime)s %(message)s")
logger = logging.getLogger("pipecat")
logger.setLevel(logging.DEBUG)

daily_api_key = os.getenv("DAILY_API_KEY", "")
daily_api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(twilio_account_sid, twilio_auth_token)


async def main(room_url: str, token: str, from_phone: str, recipient: str, sip_uri: str):
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
                default_llm,
                fl,
                tts,
                transport.output(),
                assistant_context,
                # tma_out
            ]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        runner = CustomPipelineRunner(
            context=context, summary_task=task.name, phone=recipient
        )

        @transport.event_handler("on_first_participant_joined")
        async def onParticipantJoined(transport, participant):
            transport.capture_participant_transcription(participant["id"])
            runner._set_should_summarize(True)
            await task.queue_frames([OpenAILLMContextFrame(context)])

        @transport.event_handler("on_participant_left")
        async def onParticipantLeft(transport, participant, reason):
            await summarize(context, task, recipient)

        @transport.event_handler("on_dialin_ready")
        async def onDialinReady(transport, cdata):
            # print(f"Forwarding call: {call_id} {sip_uri}")
            print("Dialing in ready")
            try:
                # The TwiML is updated using Twilio's client library
                call = twilio_client.calls.create(
                    twiml=f"<Response><Dial><Sip>{sip_uri}</Sip></Dial></Response>",
                    to=recipient,
                    from_=from_phone
                )
                print(f"Creating call: {call} {sip_uri}")
            except Exception as e:
                raise Exception(f"Failed to forward call: {str(e)}")

        await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Giterdone chatbot")
    parser.add_argument("-u", type=str, help="Room URL")
    parser.add_argument("-t", type=str, help="Token")
    parser.add_argument("-f", type=str, help="From Phone")
    parser.add_argument("-r", type=str, help="recipient")
    parser.add_argument("-s", type=str, help="sip uri")
    config = parser.parse_args()

    asyncio.run(main(config.u, config.t, config.f, config.r, config.s))
