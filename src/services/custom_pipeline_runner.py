import os
from pipecat.pipeline.runner import PipelineRunner
from intake_processor import IntakeProcessor
from pipecat.processors.frame_processor import FrameDirection
from pipecat.frames.frames import EndFrame
from pipecat.services.openai import OpenAILLMService
from pipecat.processors.aggregators.llm_response import (
    OpenAILLMContext,
    OpenAILLMContextFrame,
)


async def summarize(context, task, phone):
    summarizer_llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o"
    )
    intake = IntakeProcessor(context, summarizer_llm, phone=phone)
    summarizer_llm.register_function("summarize", intake.summarize)
    await summarizer_llm.process_frame(
        OpenAILLMContextFrame(context), FrameDirection.DOWNSTREAM
    )
    await task.queue_frame(EndFrame())


class CustomPipelineRunner(PipelineRunner):
    def __init__(
        self,
        *,
        name: str | None = None,
        handle_sigint: bool = True,
        should_summarize: bool = False,
        context: OpenAILLMContext,
        summary_task: str,
        phone: str
    ):
        super().__init__()
        self._should_summarize = should_summarize
        self._context = context
        self._summary_task = summary_task
        self._phone = phone

    async def _sig_handler(self):
        if self._should_summarize:
            await summarize(self._context, self._tasks[self._summary_task], self._phone)

        # cancel everything
        await super()._sig_handler()

    def _set_should_summarize(self, should: bool):
        self._should_summarize = should
