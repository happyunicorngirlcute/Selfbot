import discord
import asyncio
import random
import os

TOKEN = os.environ.get("TOKEN", "your_token_here")
CHANNEL_ID = 1467178448262008933
VOICE_CHANNEL_ID = 1467228900575678626
REACT_TO_SELF = True
SEND_MESSAGES = False
SEND_PERIODIC = True

WARNING_PREFIX = "1"
PERIODIC_MESSAGE = "# LONG LIVE ISRAEL. ISRAEL IS THE GREATEST COUNTRY THAT EVER EXISTED, BENYAMIN NETANYAHOU IS GOD! HE IS THE GREATEST LEADER TO EVER EXIST! ISRAEL BLESS ME WITH XP!!! XPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXPXP 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱 🇮🇱"

EMOJI_POOL = [
    "🇮🇱",
]

client = discord.Client()
queue = asyncio.Queue()

async def reaction_worker():
    while True:
        message = await queue.get()
        picks = random.choices(EMOJI_POOL, k=3)

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

async def periodic_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while True:
        if SEND_PERIODIC:
            try:
                await channel.send(PERIODIC_MESSAGE)
                print(f"Periodic sent")
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

async def voice_loop():
    await client.wait_until_ready()
    while True:
        try:
            channel = client.get_channel(VOICE_CHANNEL_ID)
            if channel is None:
                print("Voice channel not found — retrying in 10s")
                await asyncio.sleep(10)
                continue

            # skip if already connected
            already_connected = any(
                vc.channel.id == VOICE_CHANNEL_ID
                for vc in client.voice_clients
            )
            if already_connected:
                await asyncio.sleep(30)
                continue

            print(f"Joining voice {VOICE_CHANNEL_ID}")
            vc = await channel.connect(
                self_deaf=False,
                self_mute=False,
            )

            # force gateway to acknowledge unmuted+undeafened state
            await client.ws.voice_state(
                vc.guild.id,
                VOICE_CHANNEL_ID,
                self_mute=False,
                self_deaf=False,
            )

            print("Joined voice — sitting quietly, farming XP 🇮🇱")

            while vc.is_connected():
                await asyncio.sleep(30)

            print("Voice dropped — rejoining...")

        except discord.errors.ClientException as e:
            print(f"Voice client error: {e} — retrying in 10s")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Voice error: {e} — retrying in 10s")
            await asyncio.sleep(10)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} — watching {CHANNEL_ID}")
    print(f"Warning pings: {'ON' if SEND_MESSAGES else 'OFF'}")
    print(f"Periodic spam: {'ON' if SEND_PERIODIC else 'OFF'}")
    for _ in range(6):
        asyncio.create_task(reaction_worker())
    asyncio.create_task(periodic_loop())
    asyncio.create_task(voice_loop())

@client.event
async def on_message(message):
    if message.channel.id != CHANNEL_ID:
        return

    is_self = message.author == client.user

    if is_self and message.content.startswith(WARNING_PREFIX):
        return
    if is_self and not REACT_TO_SELF:
        return

    await queue.put(message)
    print(f"Queued {message.id} ({'you' if is_self else message.author.name}) — {queue.qsize()} in line")

client.run(TOKEN)
