from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services import runner

router = APIRouter()

@router.post("/create", response_class=JSONResponse)
async def createRoom() -> JSONResponse:
    room, sip_endpoint, token = await runner.createDailyRoom()

    return JSONResponse({"room_url": room, "sip": sip_endpoint, "token": token})

@router.get("/get", response_class=JSONResponse)
async def getRoom(room_url: str) -> JSONResponse:
    room, sip_endpoint, token = await runner.getDailyRoom(room_url)

    return JSONResponse({"room_url": room, "sip": sip_endpoint, "token": token})
