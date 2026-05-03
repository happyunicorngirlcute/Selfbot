import discord
import asyncio
import random

TOKEN = "MTQzOTkxOTEyNDc3NTE3ODM3Mg.GdGQ_R.oaUJ27nNtxL9ps3uMiY4qPj_votymvPVrS9DC4"
CHANNEL_ID = 1495230950513316021
REACT_TO_SELF = True
SEND_MESSAGES = False  # ← flip False to reactions-only mode

WARNING_PREFIX = "WE LOVE ISRAEL"

EMOJI_POOL = [
    "😀","😁","😂","🤣","😃","😄","😅","😆","😇","😈",
    "👿","😉","😊","😋","😌","😍","🥰","😎","🤓","🧐",
    "😏","😒","😞","😔","😟","😕","🙁","☹️","😣","😖",
    "😫","😩","🥺","😢","😭","😤","😠","😡","🤬","😳",
    "🥵","🥶","😱","😨","😰","😥","😓","🤗","🤔","🫠",
    "🤭","🤫","🤥","😶","😐","😑","😬","🙄","😯","😦",
    "😧","😮","😲","🥱","😴","🤤","😪","😵","🤯","🥴",
    "💀","☠️","👻","👽","🤖","👾","🎃","🫡","🗿","🤡",
    "💩","👹","👺","🙈","🙉","🙊","🐸","🦆","🦅","🦉",
    "🦊","🐺","🦁","🐯","🐻","🐼","🐨","🦝","🐧","🦈",
    "🐙","🦑","🦞","🦀","🐡","🐠","🐟","🦋","🐛","🪲",
    "👀","👁️","🫦","👅","🧠","🫀","🦴","👃","👂","🦶",
    "👣","💅","🤙","🖕","✌️","🤞","🫰","🤘","🤟","👋",
    "🫵","☝️","👆","👇","👉","👈","🙏","🤝","🫶","❤️",
    "💔","🔥","✨","💫","⚡","🌊","🌈","❄️","🌙","☀️",
    "⭐","🎉","🎊","🎯","🎲","🎰","🃏","🎭","🎪","🚀",
    "🛸","💎","🔮","🗡️","⚔️","🛡️","🪄","🧨","💣","🔫",
    "🪓","⚰️","🧲","🔐","🗝️","📿","🧿","🪬","🔯","☯️",
    "🍆","🍑","🌶️","🍄","🍕","🍔","🌮","🍜","🍣","🧁",
    "🍩","🍪","🎂","🍷","🍸","🍺","🥂","☕","🧃","🥛",
]

client = discord.Client()
queue = asyncio.Queue()

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
            print(f"Cooling down {cooldown:.2f}s before sending warning")
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

@client.event
async def on_ready():
    print(f"Logged in as {client.user} — watching channel {CHANNEL_ID}")
    print(f"Messages: {'ON' if SEND_MESSAGES else 'OFF'}")
    asyncio.create_task(reaction_worker())

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