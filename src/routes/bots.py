import asyncio
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from services import runner
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client

router = APIRouter()

twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(twilio_account_sid, twilio_auth_token)


@router.post("/call-bot", response_class=PlainTextResponse)
async def createBot(recipient: str) -> PlainTextResponse:
    room_url, sip_endpoint, token = await runner.createDailyRoom()
    twilio_phone = os.getenv("TWILIO_PHONE")

    asyncio.create_task(
        runner.joinDailyRoom(room_url, token, sip_endpoint, twilio_phone, recipient)
    )

    return twilio_phone


@router.get("/status/{pid}")
async def getStatus(pid: int):
    status = await runner.viewProcessStatus(pid)

    return JSONResponse({"bot_id": pid, "status": status})


@router.get("/get-all")
async def getAll():
    bots = await runner.listAllBots()

    return JSONResponse(bots)


@router.delete("/remove-bot/all")
async def deleteBots():
    removed = await runner.cleanup()

    return JSONResponse(removed)


@router.delete("/remove-bot/{pid}")
async def deleteBot(pid: int):
    await runner.cleanup(pid)

    return PlainTextResponse(f"Removed {pid}")
