import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Web Server to Keep Bot Alive ---
app = Flask("")

@app.route("/")
def home():
    return "Aetheris Core is alive."

def run_web_server():
    # Use PORT from environment or default to 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()
    logging.info("Keep-alive server started.")

# --- Bot Setup ---
async def main():
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    GUILD_ID = os.getenv("GUILD_ID")
    DB_FILE = "aetheris.db"

    if not os.path.exists(DB_FILE):
        logging.warning(f"Database file '{DB_FILE}' not found. Attempting to create it...")
        try:
            import database_setup
            database_setup.setup_database()
        except Exception as e:
            logging.error(f"Failed to setup database: {e}")
            return

    if TOKEN is None:
        logging.error("CRITICAL: DISCORD_TOKEN environment variable not set.")
        return

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="/", intents=intents)

    @bot.event
    async def on_ready():
        logging.info(f"Logged in as {bot.user.name} ({bot.user.id})")
        await load_cogs()
        await sync_commands()

    async def load_cogs():
        logging.info("--- Loading Cogs ---")
        folder = "cogs"
        if not os.path.exists(folder):
            logging.error(f"Cogs folder '{folder}' not found.")
            return

        for filename in os.listdir(f"./{folder}"):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_name = f"{folder}.{filename[:-3]}"
                try:
                    await bot.load_extension(cog_name)
                    logging.info(f"Successfully loaded cog: {cog_name}")
                except Exception as e:
                    logging.error(f"Failed to load cog {cog_name}: {e}", exc_info=True)
        logging.info("--- Cog loading complete ---")

    async def sync_commands():
        logging.info("--- Syncing commands ---")
        target_guild = discord.Object(id=GUILD_ID) if GUILD_ID else None
        try:
            if target_guild:
                logging.info(f"Syncing commands to guild: {GUILD_ID}")
                bot.tree.copy_global_to(guild=target_guild)
                synced = await bot.tree.sync(guild=target_guild)
            else:
                logging.info("Syncing commands globally.")
                synced = await bot.tree.sync()
            logging.info(f"Synced {len(synced)} command(s).")
        except Exception as e:
            logging.error(f"Failed to sync commands: {e}")
        logging.info("--- Command syncing complete ---")
        logging.info("Bot is ready and online.")

    keep_alive()
    try:
        await bot.start(TOKEN)
    except Exception as e:
        logging.error(f"Bot failed to start: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot is shutting down.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
