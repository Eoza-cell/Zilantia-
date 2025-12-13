import asyncio
import discord
from discord.ext import commands, tasks
from discord import ui
import os
import random
import requests
import sqlite3
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

# Load environment variables from .env file
load_dotenv()

# Get the token from the environment variables
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up the bot with necessary intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# --- Database Connection ---
DB_FILE = 'arcanes.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Data Access Functions ---
def get_player(user_id: int) -> sqlite3.Row | None:
    conn = get_db_connection()
    player = conn.execute('SELECT * FROM players WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return player

def create_player_if_not_exists(user_id: int, user_name: str, avatar_url: str):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO players (user_id, user_name, user_avatar_url, rang, pp, luxium, ss_validated)
        VALUES (?, ?, ?, 'F', 0, 100, FALSE)
        ON CONFLICT(user_id) DO NOTHING
    ''', (user_id, user_name, avatar_url))
    conn.commit()
    conn.close()

def update_player_pp_and_rank(user_id: int, pp_gain: int):
    conn = get_db_connection()
    player = conn.execute('SELECT pp FROM players WHERE user_id = ?', (user_id,)).fetchone()
    if not player:
        conn.close()
        return

    new_pp = player['pp'] + pp_gain

    if new_pp < 10: new_rank = 'F'
    elif new_pp < 25: new_rank = 'E'
    elif new_pp < 40: new_rank = 'D'
    elif new_pp < 60: new_rank = 'C'
    elif new_pp < 80: new_rank = 'B'
    elif new_pp < 95: new_rank = 'A'
    elif new_pp < 120: new_rank = 'S'
    else: new_rank = 'S'

    conn.execute('UPDATE players SET pp = ?, rang = ? WHERE user_id = ?', (new_pp, new_rank, user_id))
    conn.commit()
    conn.close()

def create_territory(name: str, type: str, owner_id: int):
    conn = get_db_connection()
    conn.execute('INSERT INTO territories (name, type, owner_id) VALUES (?, ?, ?)', (name, type, owner_id))
    conn.commit()
    conn.close()

def get_player_territories(owner_id: int):
    conn = get_db_connection()
    territories = conn.execute('SELECT * FROM territories WHERE owner_id = ?', (owner_id,)).fetchall()
    conn.close()
    return territories

def get_all_territories():
    conn = get_db_connection()
    territories = conn.execute('SELECT * FROM territories').fetchall()
    conn.close()
    return territories

def update_player_luxium(user_id: int, amount: int):
    conn = get_db_connection()
    conn.execute('UPDATE players SET luxium = luxium + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# --- Background Tasks ---
@tasks.loop(hours=24)
async def daily_luxium_distribution():
    print("Running daily Luxium distribution...")
    territories = get_all_territories()
    income_map = {'village': 10, 'ville': 50, 'cité': 150, 'royaume': 500, 'empire': 2000}
    for territory in territories:
        income = income_map.get(territory['type'], 0)
        if income > 0:
            try:
                update_player_luxium(territory['owner_id'], income)
            except sqlite3.Error as e:
                print(f"Failed to give Luxium. Error: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    if not daily_luxium_distribution.is_running():
        daily_luxium_distribution.start()

# --- Bot Commands ---
@bot.tree.command(name="start", description="Commencez votre aventure dans l'Ère des Arcanes.")
async def start(interaction: discord.Interaction):
    create_player_if_not_exists(interaction.user.id, interaction.user.name, str(interaction.user.avatar.url) if interaction.user.avatar else '')
    welcome_message = (
        f"**Bienvenue dans l'Ère des Arcanes, {interaction.user.mention} !**\n\n"
        "Un monde où la magie, le pouvoir et les territoires façonnent le destin vous attend.\n\n"
        "Voici quelques commandes pour bien commencer :\n"
        "• `/profile` : Consultez votre rang magique et votre richesse.\n"
        "• `/progresser` : Entraînez-vous pour augmenter votre puissance.\n"
        "• `/fonder village [nom]` : Créez votre premier territoire."
    )
    await interaction.response.send_message(welcome_message)

@bot.tree.command(name="profile", description="Affiche votre profil de l'Ère des Arcanes.")
async def profile(interaction: discord.Interaction):
    create_player_if_not_exists(interaction.user.id, interaction.user.name, str(interaction.user.avatar.url) if interaction.user.avatar else '')
    player = get_player(interaction.user.id)
    embed = discord.Embed(title=f"Profil de {player['user_name']}", color=discord.Color.purple())
    if player['user_avatar_url']:
        embed.set_thumbnail(url=player['user_avatar_url'])
    embed.add_field(name="👑 Rang Magique", value=f"**{player['rang']}**", inline=True)
    embed.add_field(name="✨ Points de Puissance (PP)", value=f"{player['pp']}", inline=True)
    embed.add_field(name="💰 Luxium", value=f"{player['luxium']}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="progresser", description="Entraînez-vous pour gagner en puissance.")
async def progresser(interaction: discord.Interaction):
    user_id = interaction.user.id
    create_player_if_not_exists(user_id, interaction.user.name, str(interaction.user.avatar.url) if interaction.user.avatar else '')
    player_before = get_player(user_id)
    pp_gain = random.randint(1, 5)
    update_player_pp_and_rank(user_id, pp_gain)
    player_after = get_player(user_id)
    message = f"Vous vous êtes entraîné et avez gagné **{pp_gain} PP**. Total : **{player_after['pp']}**."
    if player_before['rang'] != player_after['rang']:
        message += f"\n\n**Félicitations !** Vous avez atteint le **Rang {player_after['rang']}** !"
    await interaction.response.send_message(message)

@bot.tree.command(name="fonder", description="Fonde un nouveau territoire.")
async def fonder(interaction: discord.Interaction, type_territoire: str, nom: str):
    user_id = interaction.user.id
    valid_types = ["village", "ville", "cité", "royaume", "empire"]
    if type_territoire.lower() not in valid_types:
        await interaction.response.send_message(f"Type invalide. Valides : {', '.join(valid_types)}", ephemeral=True)
        return
    create_player_if_not_exists(user_id, interaction.user.name, str(interaction.user.avatar.url) if interaction.user.avatar else '')
    create_territory(nom, type_territoire.lower(), user_id)
    await interaction.response.send_message(f"Félicitations ! Vous avez fondé le **{type_territoire}** de **{nom}**.")

@bot.tree.command(name="territoire", description="Affiche les informations de vos territoires.")
async def territoire(interaction: discord.Interaction):
    user_id = interaction.user.id
    territories = get_player_territories(user_id)
    if not territories:
        await interaction.response.send_message("Vous ne possédez aucun territoire. Utilisez `/fonder`.", ephemeral=True)
        return
    embed = discord.Embed(title=f"Territoires de {interaction.user.name}", color=discord.Color.gold())
    for ter in territories:
        embed.add_field(name=f"🏰 {ter['name']} ({ter['type'].capitalize()})",
                        value=f"**Population:** {ter['population']}\n**Loyauté:** {ter['loyalty']}%",
                        inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="image", description="Génère une image d'ambiance de l'Ère des Arcanes.")
async def image(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    full_prompt = f"fantasy medieval, magical, vibrant, {prompt}, cinematic, photorealistic, 4k"
    image_url = f"https://image.pollinations.ai/prompt/{full_prompt}"
    try:
        response = requests.head(image_url, timeout=10)
        response.raise_for_status()
        embed = discord.Embed(title="Image de l'Ère des Arcanes", description=f"Prompt : `{prompt}`", color=discord.Color.purple())
        embed.set_image(url=image_url)
        embed.set_footer(text="Généré avec Pollinations.ai")
        await interaction.followup.send(embed=embed)
    except requests.exceptions.RequestException as e:
        await interaction.followup.send("Le service de génération d'images est indisponible.", ephemeral=True)

if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' not found. Please run `python3 database_setup.py` first.")
        exit()
    if TOKEN is None:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        keep_alive()
        bot.run(TOKEN)
