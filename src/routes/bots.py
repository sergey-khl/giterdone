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

    room, proc_pid = runner.joinDailyRoom(room_url, phone)

    # Grab a token for the user to join with
    return JSONResponse(
        {"room_url": room.url, "sipUri": room.config.sip_endpoint, "proc_pid": proc_pid}
    )


@router.get("/status/{pid}")
def getStatus(pid: int):
    status = runner.viewProcessStatus(pid)

    return JSONResponse({"bot_id": pid, "status": status})


@router.delete("/remove-bot/all")
def deleteBots():
    removed = runner.cleanup()

    return JSONResponse(removed)


@router.delete("/remove-bot/{pid}")
def deleteBot(pid: int):
    runner.cleanup(pid)

    return PlainTextResponse(f"Removed {pid}")
