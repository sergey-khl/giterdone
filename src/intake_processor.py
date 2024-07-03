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
        self._context.set_tools([UPDATE_TODO])
        logger.info(f"context !!!: {self._context}")
        self._functions = ["update_todo_list"]
        self._todo = []

    async def updateTodo(self, llm, args):
        # self._context.add_message(
        #     {
        #         "role": "system",
        #         "content": "Next, succinctly ask if there are any other modifications to be made.",
        #     }
        # )
        logger.info(f"!!! Saving PAPAPA: {self._todo}, {args}")
        if args["todo_items"] == self._todo:
            return None
        self._todo = args["todo_items"]
        logger.info(f"!!! Saving MAMAMAMA: {args}")
        # We don't need the function call in the context, so just return a new
        # system message and let the framework re-prompt
        return [
            {
                "role": "system",
                "content": "Next, succinctly ask if there are any other modifications to be made. Do not call update_todo_list without a new user response.",
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
