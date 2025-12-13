import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- Web Server to Keep Bot Alive ---
app = Flask('')

@app.route('/')
def home():
    return "Arcanes Core is alive."

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# --- Bot Setup ---
async def main():
    # Load environment variables
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    DB_FILE = 'arcanes.db'

    if not os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' not found. Please run `python3 database_setup.py` first.")
        return

    if TOKEN is None:
        print("Error: DISCORD_TOKEN environment variable not set.")
        return

    # Set up intents
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    # Create bot instance
    bot = commands.Bot(command_prefix='/', intents=intents)

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name}')
        print(f"Synced {len(await bot.tree.sync())} command(s)")

    # Load all cogs from the 'cogs' directory
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Successfully loaded cog: {filename}")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")

    # Start the keep_alive server
    keep_alive()

    # Start the bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot is shutting down.")
