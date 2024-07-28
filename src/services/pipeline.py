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
    DailyDialinSettings,
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
twilioclient = Client(twilio_account_sid, twilio_auth_token)


async def main(room_url: str, token: str, phone: str, call_id: str, sip_uri: str):
    async with aiohttp.ClientSession() as session:
        # diallin_settings = DailyDialinSettings(
        #     call_id=dial_code, call_domain="bear.daily.co"
        # )

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
            context=context, summary_task=task.name, phone=phone
        )

        @transport.event_handler("on_first_participant_joined")
        async def onParticipantJoined(transport, participant):
            transport.capture_participant_transcription(participant["id"])
            runner._set_should_summarize(True)
            await task.queue_frames([OpenAILLMContextFrame(context)])

        @transport.event_handler("on_participant_left")
        async def onParticipantLeft(transport, participant, reason):
            await summarize(context, task, phone)

        @transport.event_handler("on_dialin_ready")
        async def onDialinReady(transport, cdata):
            # For Twilio, Telnyx, etc. You need to update the state of the call
            # and forward it to the sip_uri..
            print(f"Forwarding call: {call_id} {sip_uri}")

            try:
                # The TwiML is updated using Twilio's client library
                call = twilioclient.calls(call_id).update(
                    twiml=f"<Response><Dial><Sip>{sip_uri}</Sip></Dial></Response>"
                )
            except Exception as e:
                raise Exception(f"Failed to forward call: {str(e)}")

        await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Giterdone chatbot")
    parser.add_argument("-u", type=str, help="Room URL")
    parser.add_argument("-t", type=str, help="Token")
    parser.add_argument("-p", type=str, help="Phone")
    parser.add_argument("-c", type=str, help="call id")
    parser.add_argument("-s", type=str, help="sip uri")
    # parser.add_argument("-d", type=str, help="Call Domain")
    config = parser.parse_args()

    asyncio.run(main(config.u, config.t, config.p, config.c, config.s))
