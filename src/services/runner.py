import asyncio
import atexit
import os
import signal
import subprocess

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomObject,
    DailyRoomParams,
    DailyRoomProperties,
    DailyRoomSipParams,
)
import requests

MAX_SESSION_TIME = 5 * 60  # 5 minutes


class DailyDeletedObject(BaseModel):
    deleted: bool
    name: str


daily_api_key = os.getenv("DAILY_API_KEY", "")
daily_api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
daily_rest_helper = DailyRESTHelper(
    daily_api_key,
    daily_api_url,
)
daily_rest_helper.daily_api_key = daily_api_key
daily_rest_helper.daily_api_url = daily_api_url

# Bot sub-process dict for status reporting and concurrency control
bots = {}
# created rooms
rooms = {}


async def cleanup(pid: int = None) -> list[str]:
    removed = []
    # Clean up function, just to be extra safe
    if pid:
        bot = bots.get(pid)

        # If the subprocess doesn't exist, return an error
        if not bot:
            raise HTTPException(
                status_code=404, detail=f"Bot with process id: {pid} not found"
            )

        await terminateBot(bot[0])
        removed.append(pid)
    else:
        # make copy
        removed = list(bots.keys())
        for pid in removed:
            await terminateBot(bots[pid][0])
    return removed


async def terminateBot(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        print("Process terminated due to timeout or early exit.")
    except OSError:
        print("Process already terminated.")

    try:
        del bots[proc.pid]
    except Exception as e:
        print(f"cannot delete from bots table: {e}")


@atexit.register
def shutdown():
    print("Shutting down")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cleanup())


"""
join a daily room
"""


async def joinDailyRoom(room_url, token, sip_endpoint, from_phone, recipient):
    num_bots_in_room = sum(
        1 for bot in bots.values() if bot[1] == room_url and bot[0].poll() is None
    )
    print("number of bots in room ", num_bots_in_room)
    if num_bots_in_room >= 1:
        raise HTTPException(
            status_code=500, detail=f"Max bot limited reach for room: {room_url}"
        )

    bot_proc = f"python3 -m pipeline -u {room_url} -t {token} -f {from_phone} -r {recipient} -s {sip_endpoint}"

    try:
        # create async process and handle timeout in the background
        proc = await asyncio.create_subprocess_shell(
            bot_proc,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            preexec_fn=os.setsid,
        )
        pid = proc.pid
        bots[pid] = (proc, room_url)
        print(f"creating bot subprocess {pid}")

        # Set a timeout for the subprocess
        timeout = 60

        async def monitorProcess():
            await asyncio.sleep(timeout)
            if proc.returncode is None:  # If process is still running
                print("Process timed out.")
                await terminateBot(proc)

        # Schedule the timeout task
        timeout_task = asyncio.create_task(monitorProcess())

        async def readStream(stream, callback):
            while True:
                line = await stream.readline()
                if not line:
                    break
                callback(line.decode().strip())

        # Schedule reading stdout and stderr
        await asyncio.gather(
            readStream(proc.stdout, lambda x: print(f"stdout: {x}")),
            readStream(proc.stderr, lambda x: print(f"stderr: {x}")),
            proc.wait(),
        )

        # Cancel the timeout task if the process ends early
        if not timeout_task.done():
            timeout_task.cancel()

        print(f"Bot subprocess {pid} ended.")

    except asyncio.CancelledError:
        await terminateBot(proc)
        raise HTTPException(
            status_code=500, detail="Task cancelled. Terminating bot subprocess..."
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"CalledProcessError: {e}")

    except KeyboardInterrupt:
        await terminateBot(proc)
        raise HTTPException(
            status_code=500, detail="Interrupted by user. Terminating bot subprocess..."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )

    finally:
        # Ensure the subprocess is terminated
        await terminateBot(proc)


"""
Create a daily room
returns daily room url, sip endpoint and token
"""


async def createDailyRoom() -> tuple[str, str, str, str]:
    try:
        params = DailyRoomParams(
            properties=DailyRoomProperties(
                # Note: these are the default values, except for the display name
                sip=DailyRoomSipParams(
                    display_name="dialin-user",
                    video=False,
                    sip_mode="dial-in",
                    num_endpoints=1,
                )
            )
        )
        room: DailyRoomObject = daily_rest_helper.create_room(params)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="failed to create room")

    print(f"Creating Daily room: {room.url} {room.config.sip_endpoint}")

    # Give the agent a token to join the session
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(status_code=500, detail="Failed to get room or token")

    rooms[room.name] = (room.url, room.config.sip_endpoint, token)

    return room.name, room.url, room.config.sip_endpoint, token


"""
Delete a daily room
returns daily room url, sip endpoint and token
"""


async def deleteDailyRoom(room_url: str) -> tuple[str, bool]:
    try:
        res = requests.delete(
            f"{daily_api_url}/rooms/{room_url}",
            headers={"Authorization": f"Bearer {daily_api_key}"},
        )

        if res.status_code != 200:
            raise Exception(f"Unable to delete room: {res.text}")

        data = res.json()

        try:
            room = DailyDeletedObject(**data)
        except ValidationError as e:
            raise Exception(f"Invalid response: {e}")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="failed to delete room")

    print(f"Deleting Daily room: {room.name} {room.deleted}")

    try:
        del rooms[room_url]
    except Exception as e:
        print(f"cannot delete from bots table: {e}")

    return room.name, room.deleted


"""
Get a daily room
returns daily room url, sip endpoint and token
"""


async def getDailyRoom(room_name: str) -> tuple[str, str, tuple]:
    try:
        room: DailyRoomObject = daily_rest_helper._get_room_from_name(room_name)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500, detail=f"failed to get existing room {room_name}"
        )

    local_room = rooms.get(room_name)
    if not local_room:
        raise HTTPException(
            status_code=404,
            detail=f"local room {room_name} not found but exists in daily",
        )

    return room.url, room.config.sip_endpoint, local_room


async def viewProcessStatus(pid: int):
    # Look up the subprocess
    proc = bots.get(pid)

    # If the subprocess doesn't exist, return an error
    if not proc:
        raise HTTPException(
            status_code=404, detail=f"Bot with process id: {pid} not found"
        )

    # Check the status of the subprocess
    if proc[0].poll() is None:
        return "running"
    else:
        return "finished"
