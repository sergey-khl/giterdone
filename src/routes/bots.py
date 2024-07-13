import asyncio
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from services import runner

router = APIRouter()


@router.post("/create-daily-bot")
async def createDailyBot(phone: str) -> JSONResponse:
    # The /daily_start_bot is invoked when a call is received on Daily's SIP URI
    # daily_start_bot will create the room, put the call on hold until
    # the bot and sip worker are ready. Daily will automatically
    # forward the call to the SIP URi when dialin_ready fires.

    room_url = os.getenv("DAILY_SAMPLE_ROOM_URL", None)

    asyncio.create_task(runner.joinDailyRoom(room_url, phone))

    # Grab a token for the user to join with
    return PlainTextResponse("started a bot")


@router.get("/status/{pid}")
async def getStatus(pid: int):
    status = await runner.viewProcessStatus(pid)

    return JSONResponse({"bot_id": pid, "status": status})


@router.delete("/remove-bot/all")
async def deleteBots():
    removed = await runner.cleanup()

    return JSONResponse(removed)


@router.delete("/remove-bot/{pid}")
async def deleteBot(pid: int):
    await runner.cleanup(pid)

    return PlainTextResponse(f"Removed {pid}")
