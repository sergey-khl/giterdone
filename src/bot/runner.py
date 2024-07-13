import atexit
import os
import signal
import subprocess
from fastapi import HTTPException
from pipecat.transports.services.helpers.daily_rest import (
    DailyRoomObject,
    DailyRESTHelper,
)

MAX_SESSION_TIME = 5 * 60  # 5 minutes


daily_rest_helper = DailyRESTHelper(
    os.getenv("DAILY_API_KEY", ""),
    os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
)

# Bot sub-process dict for status reporting and concurrency control
bots = {}


def cleanup(pid: int = None) -> list[str]:
    removed = []
    # Clean up function, just to be extra safe
    if pid:
        proc = bots.get(pid)

        # If the subprocess doesn't exist, return an error
        if not proc:
            raise HTTPException(
                status_code=404, detail=f"Bot with process id: {pid} not found"
            )

        terminateBot(proc[0])
        del bots[pid]
        removed.append(pid)
    else:
        for pid, proc in bots.items():
            terminateBot(proc[0])
            removed.append(pid)
        bots.clear()
    return removed


def terminateBot(proc):
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)


atexit.register(cleanup)

"""
Create a daily room
"""


def joinDailyRoom(room_url, phone) -> tuple[DailyRoomObject, int]:
    num_bots_in_room = sum(
        1 for proc in bots.values() if proc[1] == room_url and proc[0].poll() is None
    )
    print("number of bots in room ", num_bots_in_room)
    if num_bots_in_room >= 1:
        raise HTTPException(
            status_code=500, detail=f"Max bot limited reach for room: {room_url}"
        )

    try:
        print(f"Joining existing room: {room_url}")
        room: DailyRoomObject = daily_rest_helper.get_room_from_url(room_url)
    except Exception:
        raise HTTPException(status_code=500, detail=f"Room not found: {room_url}")

    print(f"Daily room: {room.url} {room.config.sip_endpoint}")

    # Give the agent a token to join the session
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get room or token token"
        )

    bot_proc = f"python3 -m pipeline -u {room.url} -t {token} -p {phone}"

    try:
        proc = subprocess.Popen(
            [bot_proc],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            preexec_fn=os.setsid,
        )
        bots[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    return room, proc.pid

def viewProcessStatus(pid: int):
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
