from pipecat.processors.aggregators.llm_response import (
    OpenAILLMContext,
)
from loguru import logger
from prompts import *
from typing import List

from openai._types import NotGiven, NOT_GIVEN

from openai.types.chat import (
    ChatCompletionToolParam,
)

from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.openai import OpenAILLMContext, OpenAILLMContextFrame
from pipecat.services.ai_services import AIService


class IntakeProcessor:
    def __init__(
        self,
        context: OpenAILLMContext,
        llm: AIService,
        tools: List[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._context: OpenAILLMContext = context
        self._llm = llm
        print(f"Initializing context from IntakeProcessor")
        self._context.set_tools([ACCEPT_HOT_DOG])
        self._context.add_message(BASE_PROMPT)
        # Create an allowlist of functions that the LLM can call
        self._functions = [
            "accept_hot_dog",
            "accept_mistake",
            "accept_vow",
        ]

    async def start_hot_dog(self, llm, args):
        self._context.set_tools([ACCEPT_MISTAKE])
        # self._context.add_message(
        #     {
        #         "role": "system",
        #         "content": "Next, ask the applicant what the number one mistake is when making hot dogs and call the accept_mistake function",
        #     }
        # )
        # We don't need the function call in the context, so just return a new
        # system message and let the framework re-prompt
        print("accepted hot dog: ", args["accepted"])
        return [
            {
                "role": "system",
                "content": "Next, ask the applicant what the number one mistake is when making hot dogs and call the accept_mistake function",
            }
        ]
        # await llm.process_frame(
        #     OpenAILLMContextFrame(self._context), FrameDirection.DOWNSTREAM
        # )

    async def start_mistake(self, llm, args):
        print("accepted mistake: ", args["accepted"])
        # Move on to allergies
        self._context.set_tools([ACCEPT_VOW])
        # self._context.add_message(
        #     {
        #         "role": "system",
        #         "content": "Next, ask the applicant to say 'I love hot dogs almost as much as I love America.' and call the accept_vow function.",
        #     }
        # )
        return [
            {
                "role": "system",
                "content": "Next, ask the applicant to say 'I love hot dogs almost as much as I love America.' and call the accept_vow function.",
            }
        ]
        # await llm.process_frame(
        #     OpenAILLMContextFrame(self._context), FrameDirection.DOWNSTREAM
        # )

    async def start_vow(self, llm, args):
        print("accepted vow: ", args["accepted"])
        self._context.set_tools([])
        # self._context.add_message(
        #     {
        #         "role": "system",
        #         "content": "Now, thank the user and hire them if all 3 answers are accepted.",
        #     }
        # )
        return [
            {
                "role": "system",
                "content": "Now, thank the user and hire them if all 3 answers are accepted.",
            }
        ]
        # await llm.process_frame(
        #     OpenAILLMContextFrame(self._context), FrameDirection.DOWNSTREAM
        # )

    async def save_data(self, llm, args):
        logger.info(f"!!! Saving data: {args}")
        # Since this is supposed to be "async", returning None from the callback
        # will prevent adding anything to context or re-prompting
        return None
