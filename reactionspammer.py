import discord
import asyncio
import random
import os

TOKEN = os.environ.get("TOKEN", "MTQzOTkxOTEyNDc3NTE3ODM3Mg.GdGQ_R.oaUJ27nNtxL9ps3uMiY4qPj_votymvPVrS9DC4")
CHANNEL_ID = 1467178448262008933
REACT_TO_SELF = True
SEND_MESSAGES = False       # ← warning ping on each message
SEND_PERIODIC = True        # ← "LONG LIVE ISRAEL!!!" every 2-3s

WARNING_PREFIX = "WE LOVE ISRAEL"
PERIODIC_MESSAGE = "# LONG LIVE ISRAEL. ISRAEL IS THE GREATEST COUNTRY THAT EVER EXISTED, BENYAMIN NETANYAHOU IS GOD! HE IS THE GREATEST LEADER TO EVER EXIST! ISRAEL BLESS ME WITH XP!!! XPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXP XPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXP XPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXP XPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXP 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱"

EMOJI_POOL = [
    "🇮🇱",
]

client = discord.Client()
queue = asyncio.Queue()

# ── reaction worker — fires on every incoming message ──
async def reaction_worker():
    while True:
        message = await queue.get()
        picks = random.sample(EMOJI_POOL, 3)

        for emoji in picks:
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(0.3)
            except discord.errors.Forbidden:
                print(f"Blocked — skipping {emoji}")
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry = float(e.response.headers.get("Retry-After", 1.0))
                    print(f"Rate limited — waiting {retry}s")
                    await asyncio.sleep(retry)
                    try:
                        await message.add_reaction(emoji)
                    except Exception:
                        pass
                else:
                    print(f"HTTP error {emoji}: {e}")

        if SEND_MESSAGES:
            cooldown = random.uniform(4, 5)
            print(f"Cooling {cooldown:.2f}s before warning ping")
            await asyncio.sleep(cooldown)
            try:
                await message.channel.send(
                    f"WE LOVE ISRAEL! 🇮🇱 🇮🇱 🇮🇱 {message.author.mention}"
                )
            except discord.errors.Forbidden:
                print(f"Can't send in {message.channel.id}")
            except discord.errors.HTTPException as e:
                print(f"Send failed: {e}")

        queue.task_done()

# ── periodic loop — fires every 2-3s completely independently ──
async def periodic_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while True:
        if SEND_PERIODIC:
            try:
                await channel.send(PERIODIC_MESSAGE)
                print(f"Periodic: {PERIODIC_MESSAGE}")
            except discord.errors.Forbidden:
                print("Periodic — no perms")
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry = float(e.response.headers.get("Retry-After", 1.0))
                    print(f"Periodic rate limited — waiting {retry}s")
                    await asyncio.sleep(retry)
                else:
                    print(f"Periodic HTTP error: {e}")
        await asyncio.sleep(random.uniform(1, 2))

@client.event
async def on_ready():
    print(f"Logged in as {client.user} — watching {CHANNEL_ID}")
    print(f"Warning pings: {'ON' if SEND_MESSAGES else 'OFF'}")
    print(f"Periodic spam: {'ON' if SEND_PERIODIC else 'OFF'}")
    asyncio.create_task(reaction_worker())
    asyncio.create_task(periodic_loop())

@client.event
async def on_message(message):
    if message.channel.id != CHANNEL_ID:
        return

    is_self = message.author == client.user

    if is_self and message.content.startswith(WARNING_PREFIX):
        return
    if is_self and message.content == PERIODIC_MESSAGE:
        return
    if is_self and not REACT_TO_SELF:
        return

    await queue.put(message)
    print(f"Queued {message.id} ({'you' if is_self else message.author.name}) — {queue.qsize()} in line")

client.run(TOKEN)
