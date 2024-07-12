from pipecat.processors.aggregators.llm_response import (
    OpenAILLMContext,
)
from loguru import logger
from prompts import *
from typing import List
from datetime import datetime

from openai._types import NotGiven, NOT_GIVEN

from openai.types.chat import (
    ChatCompletionToolParam,
)

from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.openai import OpenAILLMContext, OpenAILLMContextFrame
from pipecat.services.ai_services import AIService
from texter import sendSms


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
        context.set_tools([SUMMARIZE])
        context.add_message(
            {
                "role": "system",
                "content": "You will now summarize the entire conversation to get an updated to do list by calling the summarize function.",
            }
        )
        logger.info(f"context !!!: {self._context}")
        self._functions = ["summarize"]
        self._todo = []

    async def summarize(self, llm, args):
        logger.info(f"setting todo items {args['todo_items']}")
        self._todo = args["todo_items"]
        await self.sendTodo()
        # We don't need the function call in the context, so just return a new
        # system message and let the framework re-prompt
        return None

    async def sendTodo(self):
        today = datetime.today()
        message = today.strftime("TODO for %d, %b %Y:")
        for item in self._todo:
            message += f"\n{item['title']}"
        logger.info(f"sending sms {message}")

        return None
