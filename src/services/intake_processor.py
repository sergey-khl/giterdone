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

from pipecat.services.openai import OpenAILLMContext
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
        self._context: OpenAILLMContext = context
        self._llm = llm
        context.set_tools([SUMMARIZE])
        context.add_message(START_SUMMARIZE)
        self._phone = kwargs.get("phone", None)
        self._functions = ["summarize"]

    async def summarize(self, llm, args):
        todo = args["todo_items"]
        today = datetime.today()
        message = today.strftime("TODO for %d, %b %Y:")
        for item in todo:
            message += f"\n{item['emoji']}\t{item['title']}"
        logger.info(f"todo {todo}")
        await self.sendTodo(message)
        # We don't need the function call in the context, so just return a new
        # system message and let the framework re-prompt
        return None

    async def sendTodo(self, message):
        logger.info(f"sending sms {message}")
        # sendSms(self._phone, message)

        return None
