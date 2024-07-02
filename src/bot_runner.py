"""
bot_runner.py

HTTP service that listens for incoming calls from either Daily or Twilio,
provisioning a room and starting a Pipecat bot in response.

Refer to README for more information.
"""
import os
import argparse
import subprocess
import signal
import atexit
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomObject
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
load_dotenv(override=True)


# ------------ Configuration ------------ #

MAX_SESSION_TIME = 5 * 60  # 5 minutes
REQUIRED_ENV_VARS = ['OPENAI_API_KEY', 'DAILY_API_KEY',
                     'DEEPGRAM_API_KEY', 'DAILY_API_URL']

# Bot sub-process dict for status reporting and concurrency control
bot_procs = {}

def cleanup(pid: int = None):
    # Clean up function, just to be extra safe
    if pid:
        proc = bot_procs.get(pid)

        # If the subprocess doesn't exist, return an error
        if not proc:
            raise HTTPException(
                status_code=404, detail=f"Bot with process id: {pid} not found")
        
        terminateBot(proc[0])
        del bot_procs[pid]
    else:
        for pid, proc in bot_procs.items():
            terminateBot(proc[0])
        bot_procs.clear()

def terminateBot(proc):
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

atexit.register(cleanup)

daily_rest_helper = DailyRESTHelper(
    os.getenv("DAILY_API_KEY", ""),
    os.getenv("DAILY_API_URL", 'https://api.daily.co/v1'))

# ----------------- API ----------------- #

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

"""
Create Daily room, When the vendor is Daily, the bot handles the call forwarding automatically,
i.e, forwards the call from the "hold music state" to the Daily Room's SIP URI.
"""
def _create_daily_room(room_url) -> tuple[DailyRoomObject, int]:
    num_bots_in_room = sum(1 for proc in bot_procs.values() if proc[1] == room_url and proc[0].poll() is None)
    print("number of bots in room ", num_bots_in_room)
    if num_bots_in_room >= 1:
        raise HTTPException(status_code=500, detail=f"Max bot limited reach for room: {room_url}")

    try:
        print(f"Joining existing room: {room_url}")
        room: DailyRoomObject = daily_rest_helper.get_room_from_url(room_url)
    except Exception:
        raise HTTPException(
            status_code=500, detail=f"Room not found: {room_url}")

    print(f"Daily room: {room.url} {room.config.sip_endpoint}")

    # Give the agent a token to join the session
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get room or token token")

    bot_proc = f"python3 -m bot_daily -u {room.url} -t {token}"

    try:
        proc = subprocess.Popen(
            [bot_proc],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            preexec_fn=os.setsid
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start subprocess: {e}")

    return room, proc.pid


@app.post("/daily_start_bot")
async def daily_start_bot() -> JSONResponse:
    # The /daily_start_bot is invoked when a call is received on Daily's SIP URI
    # daily_start_bot will create the room, put the call on hold until
    # the bot and sip worker are ready. Daily will automatically
    # forward the call to the SIP URi when dialin_ready fires.

    # Use specified room URL, or create a new one if not specified
    room_url = os.getenv("DAILY_SAMPLE_ROOM_URL", None)

    room, proc_pid = _create_daily_room(room_url)

    # Grab a token for the user to join with
    return JSONResponse({
        "room_url": room.url,
        "sipUri": room.config.sip_endpoint,
        "proc_pid": proc_pid
    })

@app.get("/status/{pid}")
def get_status(pid: int):
    # Look up the subprocess
    proc = bot_procs.get(pid)

    # If the subprocess doesn't exist, return an error
    if not proc:
        raise HTTPException(
            status_code=404, detail=f"Bot with process id: {pid} not found")

    # Check the status of the subprocess
    if proc[0].poll() is None:
        status = "running"
    else:
        status = "finished"

    return JSONResponse({"bot_id": pid, "status": status})

@app.delete("/remove-bot/all")
def get_status():
    cleanup()
    return JSONResponse(list(bot_procs.keys()))

@app.delete("/remove-bot/{pid}")
def get_status(pid: int):
    cleanup(pid)
    return JSONResponse(list(bot_procs.keys()))

# ----------------- Main ----------------- #


if __name__ == "__main__":
    # Check environment variables
    for env_var in REQUIRED_ENV_VARS:
        if env_var not in os.environ:
            raise Exception(f"Missing environment variable: {env_var}.")

    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument("--host", type=str,
                        default=os.getenv("HOST", "0.0.0.0"), help="Host address")
    parser.add_argument("--port", type=int,
                        default=os.getenv("PORT", 7860), help="Port number")
    parser.add_argument("--reload", action="store_true",
                        default=True, help="Reload code on change")

    config = parser.parse_args()

    try:
        import uvicorn

        uvicorn.run(
            "bot_runner:app",
            host=config.host,
            port=config.port,
            reload=config.reload
        )

    except KeyboardInterrupt:
        print("runner shutting down...")
