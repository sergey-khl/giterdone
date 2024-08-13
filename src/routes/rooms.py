from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services import runner

router = APIRouter()


@router.post("/create", response_class=JSONResponse)
async def createRoom() -> JSONResponse:
    name, room, sip_endpoint, token = await runner.createDailyRoom()

    return JSONResponse(
        {"name": name, "room_url": room, "sip": sip_endpoint, "token": token}
    )


@router.delete("/delete/{room_name}", response_class=JSONResponse)
async def deleteRoom(room_name: str) -> JSONResponse:
    name, deleted = await runner.deleteDailyRoom(room_name)

    return JSONResponse({"room_name": name, "deleted": deleted})


@router.get("/get/{room_name}", response_class=JSONResponse)
async def getRoom(room_name: str) -> JSONResponse:
    room, sip_endpoint, token = await runner.getDailyRoom(room_name)

    return JSONResponse({"room_url": room, "sip": sip_endpoint, "token": token})


@router.get("/get-all/daily")
async def getAllDaily():
    status = await runner.viewProcessStatus(pid)

    return JSONResponse({"bot_id": pid, "status": status})


@router.get("/get-all/local")
async def getAllLocal():
    status = await runner.viewProcessStatus(pid)

    return JSONResponse({"bot_id": pid, "status": status})
