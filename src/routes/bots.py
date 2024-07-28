import asyncio
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from services import runner
from twilio.twiml.voice_response import VoiceResponse

router = APIRouter()

@router.post("/create-bot", response_class=PlainTextResponse)
async def createBot(request: Request) -> JSONResponse:
    # The /daily_start_bot is invoked when a call is received on Daily's SIP URI
    # daily_start_bot will create the room, put the call on hold until
    # the bot and sip worker are ready. Daily will automatically
    # forward the call to the SIP URi when dialin_ready fires.

    data = {}
    try:
        # shouldnt have received json, twilio sends form data
        form_data = await request.form()
        data = dict(form_data)
    except Exception:
        pass

    room_url = os.getenv("DAILY_SAMPLE_ROOM_URL", None)
    call_id = data.get('CallSid')
    from_phone = data.get('From')

    if not call_id:
        raise HTTPException(
            status_code=500, detail="Missing 'CallSid' in request")

    asyncio.create_task(runner.joinDailyRoom(room_url, from_phone, call_id))

    # Grab a token for the user to join with
    resp = VoiceResponse()
    resp.play(
        url="http://com.twilio.sounds.music.s3.amazonaws.com/MARKOVICHAMP-Borghestral.mp3", loop=10)
    return str(resp)


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
