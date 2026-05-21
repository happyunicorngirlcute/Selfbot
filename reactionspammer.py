import discord
import asyncio
import random
import os
import time
import subprocess
from discord.http import Route

TOKEN = os.environ.get("TOKEN", "your_token_here")
CHANNEL_ID        = 1467178448262008933
VOICE_CHANNEL_ID  = 1467228900575678626
TYPING_CHANNEL_ID = 1426147773182378146

REACT_TO_SELF     = False
SEND_MESSAGES     = False
SEND_PERIODIC     = True
REACT_TO_MESSAGES = False
STREAMING         = True
TYPING_ENABLED    = True
BOT_COMMAND_ENABLED = True   # ← flip True to send as real slash command instead of text

WARNING_PREFIX = "1"

# ── what gets sent periodically ─────────────────
# if BOT_COMMAND_ENABLED is False  → sent as plain text
# if BOT_COMMAND_ENABLED is True   → executed as a real slash command interaction
PERIODIC_MESSAGE       = "/packs type:Half-Life: Alyx Collectible Pins Capsule"
BOT_ID                 = 1500119412009603092
BOT_COMMAND_NAME       = "packs"
BOT_COMMAND_OPTION_NAME  = "type"
BOT_COMMAND_OPTION_VALUE = "Half-Life: Alyx Collectible Pins Capsule"

SLOWMODE         = True
SLOWMODE_SECONDS = 3

LO_USER_ID = 1439919124775178372  # only you can run !commands

EMOJI_POOL = ["🇮🇱"]

RPC_APP_ID = "1498601983865651220"
RPC_NAME   = "Nord VPN"
RPC_DETAIL = "VPN 94.42.40.103"
RPC_STATE  = "REAL 89.90.119.186"

adaptive = {
    "react_sleep":   0.35,
    "periodic_min":  2.0,
    "periodic_max":  3.0,
    "concurrency":   1,
    "clean_windows": 0,
}

stats = {
    "rate_limit_hits":   0,
    "reaction_attempts": 0,
    "message_attempts":  0,
    "message_hits":      0,
}

sem          = [asyncio.Semaphore(1)]
_cached_cmd  = {}   # caches slash command id/version after first fetch

def rebuild_semaphore(new_count):
    sem[0] = asyncio.Semaphore(new_count)
    adaptive["concurrency"] = new_count

client = discord.Client()
queue  = asyncio.Queue()

# ── FFmpeg silence ───────────────────────────────
class FFmpegSilenceAudio(discord.AudioSource):
    def __init__(self):
        self._process = subprocess.Popen(
            ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-ar", "48000", "-ac", "2", "-f", "s16le", "-loglevel", "quiet", "pipe:1"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

    def read(self) -> bytes:
        return self._process.stdout.read(3840)

    def cleanup(self):
        self._process.kill()
        self._process.wait()

# ── stream helpers ───────────────────────────────
async def start_stream(vc):
    try:
        await client.ws.send_as_json({
            "op": 18,
            "d": {"type": "guild", "guild_id": str(vc.guild.id),
                  "channel_id": str(VOICE_CHANNEL_ID), "preferred_region": "us-east"}
        })
        print("[stream] LIVE payload sent")
    except Exception as e:
        print(f"[stream] start error: {e}")

async def stop_stream(vc):
    try:
        if vc.is_playing():
            vc.stop()
        await client.ws.send_as_json({
            "op": 18,
            "d": {"type": "guild", "guild_id": str(vc.guild.id), "channel_id": None}
        })
        print("[stream] stopped")
    except Exception as e:
        print(f"[stream] stop error: {e}")

# ── slash command helpers ────────────────────────
async def fetch_and_cache_command(guild):
    """fetch /packs from the guild and cache its id + version"""
    try:
        cmds = await guild.application_commands()
        for cmd in cmds:
            if (cmd.name.lower() == BOT_COMMAND_NAME.lower() and
                    getattr(cmd, "application_id", 0) == BOT_ID):
                _cached_cmd["id"]             = cmd.id
                _cached_cmd["version"]        = getattr(cmd, "version", 1)
                _cached_cmd["application_id"] = cmd.application_id
                print(f"[cmd] cached /{BOT_COMMAND_NAME} — id={cmd.id}")
                return True
        print(f"[cmd] /{BOT_COMMAND_NAME} not found for bot {BOT_ID}")
        return False
    except Exception as e:
        print(f"[cmd] fetch error: {e}")
        return False

async def execute_slash_command(channel):
    """fires a real slash command interaction — bot receives it as if you typed it"""
    if not _cached_cmd:
        print("[cmd] not cached — fetching now...")
        ok = await fetch_and_cache_command(channel.guild)
        if not ok:
            print("[cmd] falling back to text")
            await channel.send(PERIODIC_MESSAGE)
            return

    try:
        payload = {
            "type":           2,
            "application_id": str(_cached_cmd["application_id"]),
            "guild_id":       str(channel.guild.id),
            "channel_id":     str(channel.id),
            "session_id":     client.ws.session_id,
            "data": {
                "version": str(_cached_cmd["version"]),
                "id":      str(_cached_cmd["id"]),
                "name":    BOT_COMMAND_NAME,
                "type":    1,
                "options": [
                    {
                        "type":  3,
                        "name":  BOT_COMMAND_OPTION_NAME,
                        "value": BOT_COMMAND_OPTION_VALUE,
                    }
                ],
            },
            "nonce": str(discord.utils.time_snowflake(discord.utils.utcnow())),
        }
        await client.http.request(Route("POST", "/interactions"), json=payload)
        print(f"[cmd] /{BOT_COMMAND_NAME} executed via real interaction")

    except Exception as e:
        print(f"[cmd] interaction error: {e} — falling back to text")
        try:
            await channel.send(PERIODIC_MESSAGE)
        except Exception:
            pass

# ── discord command handler (!commands only LO can use) ──
async def handle_command(message):
    global TYPING_ENABLED, SEND_PERIODIC, REACT_TO_MESSAGES
    global STREAMING, SEND_MESSAGES, BOT_COMMAND_ENABLED

    cmd = message.content.lower().split()[0][1:]

    toggles = {
        "typing":    lambda: None,
        "periodic":  lambda: None,
        "reactions": lambda: None,
        "streaming": lambda: None,
        "messages":  lambda: None,
        "botcmd":    lambda: None,
    }

    if cmd not in toggles and cmd != "status":
        return

    if cmd == "typing":    TYPING_ENABLED       = not TYPING_ENABLED
    if cmd == "periodic":  SEND_PERIODIC        = not SEND_PERIODIC
    if cmd == "reactions": REACT_TO_MESSAGES    = not REACT_TO_MESSAGES
    if cmd == "streaming": STREAMING            = not STREAMING
    if cmd == "messages":  SEND_MESSAGES        = not SEND_MESSAGES
    if cmd == "botcmd":    BOT_COMMAND_ENABLED  = not BOT_COMMAND_ENABLED

    if cmd == "status":
        await message.channel.send(
            f"```"
            f"\ntyping:    {'ON' if TYPING_ENABLED else 'OFF'}"
            f"\nperiodic:  {'ON' if SEND_PERIODIC else 'OFF'}"
            f"\nreactions: {'ON' if REACT_TO_MESSAGES else 'OFF'}"
            f"\nstreaming: {'ON' if STREAMING else 'OFF'}"
            f"\nmessages:  {'ON' if SEND_MESSAGES else 'OFF'}"
            f"\nbotcmd:    {'ON — slash interaction' if BOT_COMMAND_ENABLED else 'OFF — plain text'}"
            f"\n```",
            delete_after=10
        )
        return

    state = {
        "typing":    TYPING_ENABLED,
        "periodic":  SEND_PERIODIC,
        "reactions": REACT_TO_MESSAGES,
        "streaming": STREAMING,
        "messages":  SEND_MESSAGES,
        "botcmd":    BOT_COMMAND_ENABLED,
    }
    await message.channel.send(
        f"`{cmd}` → **{'ON' if state[cmd] else 'OFF'}**",
        delete_after=5
    )
    print(f"[cmd] {cmd} toggled {'ON' if state[cmd] else 'OFF'} by LO")

# ── loops ────────────────────────────────────────
async def typing_loop():
    await client.wait_until_ready()
    channel = client.get_channel(TYPING_CHANNEL_ID)
    if not channel:
        print("[typing] channel not found")
        return
    print(f"[typing] endlessly typing in {TYPING_CHANNEL_ID}")
    while True:
        if TYPING_ENABLED:
            try:
                await client.http.send_typing(channel.id)
            except Exception as e:
                print(f"[typing] error: {e}")
        await asyncio.sleep(8)

async def adaptive_loop():
    await client.wait_until_ready()
    while True:
        await asyncio.sleep(30)

        total_attempts = stats["reaction_attempts"] + stats["message_attempts"]
        total_hits     = stats["rate_limit_hits"]   + stats["message_hits"]
        rate = total_hits / total_attempts if total_attempts > 0 else 0

        stats["rate_limit_hits"]   = 0
        stats["reaction_attempts"] = 0
        stats["message_attempts"]  = 0
        stats["message_hits"]      = 0

        if rate > 0.15:
            adaptive["clean_windows"] = 0
            adaptive["react_sleep"]   = min(adaptive["react_sleep"] + 0.05, 1.0)
            adaptive["periodic_min"]  = min(adaptive["periodic_min"] + 0.5, 8.0)
            adaptive["periodic_max"]  = min(adaptive["periodic_max"] + 0.5, 10.0)
            new_conc = max(1, adaptive["concurrency"] - 1)
            rebuild_semaphore(new_conc)
            print(f"[adaptive] ⬇ backing off — 429 rate {rate:.0%} | "
                  f"sleep={adaptive['react_sleep']:.2f}s "
                  f"concurrency={adaptive['concurrency']} "
                  f"periodic={adaptive['periodic_min']:.1f}-{adaptive['periodic_max']:.1f}s")

        elif rate == 0 and total_attempts > 0:
            adaptive["clean_windows"] += 1
            if adaptive["clean_windows"] >= 2:
                adaptive["react_sleep"]  = max(adaptive["react_sleep"] - 0.03, 0.15)
                adaptive["periodic_min"] = max(adaptive["periodic_min"] - 0.25, 1.0)
                adaptive["periodic_max"] = max(adaptive["periodic_max"] - 0.25, 1.5)
                new_conc = min(adaptive["concurrency"] + 1, 8)
                rebuild_semaphore(new_conc)
                adaptive["clean_windows"] = 0
                print(f"[adaptive] ⬆ pushing harder — clean window | "
                      f"sleep={adaptive['react_sleep']:.2f}s "
                      f"concurrency={adaptive['concurrency']} "
                      f"periodic={adaptive['periodic_min']:.1f}-{adaptive['periodic_max']:.1f}s")
        else:
            adaptive["clean_windows"] = 0
            if total_attempts > 0:
                print(f"[adaptive] ↔ holding steady — 429 rate {rate:.0%}")
            else:
                print(f"[adaptive] ↔ no activity this window")

async def set_rpc():
    payload = {
        "op": 3,
        "d": {
            "status": "idle", "since": 0, "afk": False,
            "activities": [{
                "name": RPC_NAME, "type": 0,
                "application_id": RPC_APP_ID,
                "details": RPC_DETAIL, "state": RPC_STATE,
                "timestamps": {"start": int(time.time() * 1000)}
            }]
        }
    }
    await client.ws.send_as_json(payload)
    print(f"RPC pushed — {RPC_NAME} | {RPC_DETAIL} | {RPC_STATE}")

async def rpc_loop():
    await client.wait_until_ready()
    while True:
        try:
            await set_rpc()
        except Exception as e:
            print(f"RPC error: {e}")
        await asyncio.sleep(1800)

async def safe_react(message, emoji):
    async with sem[0]:
        stats["reaction_attempts"] += 1
        try:
            await message.add_reaction(emoji)
            await asyncio.sleep(adaptive["react_sleep"])
        except discord.errors.Forbidden:
            print(f"Blocked — skipping {emoji}")
        except discord.errors.HTTPException as e:
            if e.status == 429:
                stats["rate_limit_hits"] += 1
                retry = float(e.response.headers.get("Retry-After", 1.0))
                print(f"Rate limited — waiting {retry}s")
                await asyncio.sleep(retry)
                try:
                    await message.add_reaction(emoji)
                except Exception:
                    pass
            else:
                print(f"HTTP error {emoji}: {e}")

async def reaction_worker():
    while True:
        message = await queue.get()
        picks = random.choices(EMOJI_POOL, k=3)
        for emoji in picks:
            await safe_react(message, emoji)

        if SEND_MESSAGES:
            await asyncio.sleep(random.uniform(4, 5))
            try:
                await message.channel.send(
                    f"WE LOVE ISRAEL! 🇮🇱 🇮🇱 🇮🇱 {message.author.mention}"
                )
            except discord.errors.Forbidden:
                print(f"Can't send in {message.channel.id}")
            except discord.errors.HTTPException as e:
                print(f"Send failed: {e}")

        queue.task_done()

async def periodic_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while True:
        if SEND_PERIODIC:
            try:
                if BOT_COMMAND_ENABLED:
                    # fires a real slash command interaction
                    await execute_slash_command(channel)
                else:
                    # sends as plain text
                    await channel.send(PERIODIC_MESSAGE)
                stats["message_attempts"] += 1
                print(f"Periodic {'[slash]' if BOT_COMMAND_ENABLED else '[text]'} sent")
            except discord.errors.Forbidden:
                print("Periodic — no perms")
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    stats["message_hits"] += 1
                    retry = float(e.response.headers.get("Retry-After", 1.0))
                    print(f"Periodic rate limited — waiting {retry}s")
                    await asyncio.sleep(retry)
                else:
                    print(f"Periodic HTTP error: {e}")

        base  = SLOWMODE_SECONDS + 1.5
        extra = random.uniform(
            max(adaptive["periodic_min"], 0),
            max(adaptive["periodic_max"], 0.5),
        )
        await asyncio.sleep(base + extra)

async def voice_loop():
    await client.wait_until_ready()
    while True:
        try:
            channel = client.get_channel(VOICE_CHANNEL_ID)
            if channel is None:
                print("Voice channel not found — retrying in 10s")
                await asyncio.sleep(10)
                continue

            already_connected = any(
                vc.channel.id == VOICE_CHANNEL_ID
                for vc in client.voice_clients
            )
            if already_connected:
                await asyncio.sleep(30)
                continue

            print(f"Joining voice {VOICE_CHANNEL_ID}")
            vc = await channel.connect(self_deaf=False, self_mute=False)
            await client.ws.voice_state(
                vc.guild.id, VOICE_CHANNEL_ID,
                self_mute=False, self_deaf=False,
            )

            if STREAMING:
                await asyncio.sleep(1)
                source = FFmpegSilenceAudio()
                vc.play(source, after=lambda e: print(f"[stream] audio ended: {e}"))
                await start_stream(vc)
                print("Joined voice — streaming silence 🇮🇱")
            else:
                print("Joined voice — farming XP 🇮🇱")

            while vc.is_connected():
                if STREAMING and not vc.is_playing():
                    source = FFmpegSilenceAudio()
                    vc.play(source, after=lambda e: print(f"[stream] restarted: {e}"))
                await asyncio.sleep(10)

            print("Voice dropped — rejoining...")
            if STREAMING:
                await stop_stream(vc)

        except discord.errors.ClientException as e:
            print(f"Voice client error: {e} — retrying in 10s")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Voice error: {e} — retrying in 10s")
            await asyncio.sleep(10)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} — watching {CHANNEL_ID}")
    print(f"Reactions:      {'ON' if REACT_TO_MESSAGES else 'OFF'}")
    print(f"Warning pings:  {'ON' if SEND_MESSAGES else 'OFF'}")
    print(f"Periodic spam:  {'ON' if SEND_PERIODIC else 'OFF'}")
    print(f"Bot command:    {'ON — slash interaction' if BOT_COMMAND_ENABLED else 'OFF — plain text'}")
    print(f"Streaming:      {'ON — FFmpeg stream' if STREAMING else 'OFF'}")
    print(f"Typing loop:    {'ON' if TYPING_ENABLED else 'OFF'}")
    print(f"Adaptive:       ON — tuning every 30s")

    # pre-cache the slash command so first periodic fires instantly
    if BOT_COMMAND_ENABLED:
        for guild in client.guilds:
            ok = await fetch_and_cache_command(guild)
            if ok:
                break

    for _ in range(5):
        asyncio.create_task(reaction_worker())
    asyncio.create_task(periodic_loop())
    asyncio.create_task(voice_loop())
    asyncio.create_task(rpc_loop())
    asyncio.create_task(adaptive_loop())
    asyncio.create_task(typing_loop())

@client.event
async def on_message(message):
    # LO-only command system — works in any channel
    if message.author.id == LO_USER_ID and message.content.startswith("!"):
        await handle_command(message)
        return

    if message.channel.id != CHANNEL_ID:
        return

    is_self = message.author == client.user

    if is_self and message.content.startswith(WARNING_PREFIX):
        return
    if is_self and not REACT_TO_SELF:
        return

    if REACT_TO_MESSAGES:
        await queue.put(message)
        print(f"Queued {message.id} ({'you' if is_self else message.author.name}) — {queue.qsize()} in line")

client.run(TOKEN)
