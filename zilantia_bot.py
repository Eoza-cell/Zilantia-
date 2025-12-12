import discord
from discord.ext import commands
from discord import ui
import os
import random
import json
import requests
import sqlite3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the token from the environment variables
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up the bot with necessary intents
intents = discord.Intents.default()
intents.members = True # Required to access member information

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    """Prints a message to the console when the bot is connected."""
    print(f'Logged in as {bot.user.name}')
    print('------')
    try:
        # Sync the command tree
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="hello", description="Says hello to the user")
async def hello(interaction: discord.Interaction):
    """A simple command that says hello to the user."""
    await interaction.response.send_message(f"Hello {interaction.user.mention}! I am Zilantia Core, ready to serve.")

# --- Game Data Structures ---

class Item:
    def __init__(self, name, description):
        self.name = name
        self.description = description
    def to_dict(self):
        return self.__dict__

class PNJ:
    def __init__(self, name, description, system_prompt):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt # Personality for the AI
    def to_dict(self):
        return self.__dict__

class Enemy:
    def __init__(self, name, health, damage):
        self.name = name
        self.health = health
        self.damage = damage
    def to_dict(self):
        return self.__dict__

class Location:
    def __init__(self, name, description, pnjs=None, items=None, exits=None, enemies=None):
        self.name = name
        self.description = description
        self.pnjs = pnjs if pnjs is not None else []
        self.items = items if items is not None else []
        self.exits = exits if exits is not None else {}
        self.enemies = enemies if enemies is not None else []

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "pnjs": [pnj.to_dict() for pnj in self.pnjs],
            "items": [item.to_dict() for item in self.items],
            "exits": self.exits,
            "enemies": [enemy.to_dict() for enemy in self.enemies]
        }

class Mission:
    def __init__(self, id, name, description, start_objective, end_objective):
        self.id = id
        self.name = name
        self.description = description
        self.start_objective = start_objective # e.g., {"action": "interact", "target": "Colis suspect"}
        self.end_objective = end_objective   # e.g., {"action": "interact", "target": "Contact de l'Ombre"}

available_missions = {
    "livraison_sombre": Mission(
        id="livraison_sombre",
        name="Livraison Sombre",
        description="Un mystérieux colis doit être récupéré dans le Quartier Pauvre et livré à un contact sur le Port. Discrétion absolue.",
        start_objective={"target": "Colis suspect"},
        end_objective={"target": "Contact de l'Ombre"}
    )
}

class Player:
    def __init__(self, user_id, user_name, user_avatar_url, race, pouvoir):
        self.user_id = user_id
        self.user_name = user_name
        self.user_avatar_url = user_avatar_url
        self.race = race
        self.pouvoir = pouvoir
        self.niveau = 1
        self.health = 100
        self.traits_uniques = "Aucun pour le moment."
        self.artefact = "Aucun pour le moment."
        self.location_key = None
        self.active_mission_id = None
        self.mission_progress = {} # e.g., {"package_collected": True}

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_avatar_url": self.user_avatar_url,
            "race": self.race,
            "pouvoir": self.pouvoir,
            "niveau": self.niveau,
            "health": self.health,
            "traits_uniques": self.traits_uniques,
            "artefact": self.artefact,
            "location_key": self.location_key,
            "active_mission_id": self.active_mission_id,
            "mission_progress": self.mission_progress
        }

    @classmethod
    def from_dict(cls, data):
        player = cls(
            user_id=data["user_id"],
            user_name=data["user_name"],
            user_avatar_url=data["user_avatar_url"],
            race=data["race"],
            pouvoir=data["pouvoir"]
        )
        player.niveau = data["niveau"]
        player.health = data.get("health", 100)
        player.traits_uniques = data["traits_uniques"]
        player.artefact = data["artefact"]
        player.location_key = data["location_key"]
        player.active_mission_id = data.get("active_mission_id")
        player.mission_progress = data.get("mission_progress", {})
        return player

# --- Database Connection ---

DB_FILE = 'zilantia.db'

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Data Access Functions ---

def get_player(user_id):
    """Retrieves a player's data from the database."""
    conn = get_db_connection()
    player = conn.execute('SELECT * FROM players WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return player

def create_or_update_player(user_id, user_name, avatar_url, race, pouvoir):
    """Creates a new player or updates an existing one."""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO players (user_id, user_name, user_avatar_url, race, pouvoir, location_key)
        VALUES (?, ?, ?, ?, ?, 'quartier_pauvre')
        ON CONFLICT(user_id) DO UPDATE SET
        user_name = excluded.user_name,
        user_avatar_url = excluded.user_avatar_url,
        race = excluded.race,
        pouvoir = excluded.pouvoir
    ''', (user_id, user_name, avatar_url, race, pouvoir))
    conn.commit()
    conn.close()

def update_player_location(user_id, new_location_key):
    """Updates a player's current location."""
    conn = get_db_connection()
    conn.execute('UPDATE players SET location_key = ? WHERE user_id = ?', (new_location_key, user_id))
    conn.commit()
    conn.close()

def get_location_details(location_key):
    """Retrieves full details for a location, including PNJs, items, etc."""
    conn = get_db_connection()
    location_data = {}

    loc = conn.execute('SELECT * FROM locations WHERE key = ?', (location_key,)).fetchone()
    if not loc:
        conn.close()
        return None
    location_data['details'] = loc

    location_data['pnjs'] = conn.execute('SELECT * FROM pnjs WHERE location_key = ?', (location_key,)).fetchall()
    location_data['items'] = conn.execute('SELECT * FROM items WHERE location_key = ?', (location_key,)).fetchall()
    location_data['enemies'] = conn.execute('SELECT * FROM enemies WHERE location_key = ?', (location_key,)).fetchall()

    # For now, exits are static, but could be moved to the DB later
    exits = {
        'quartier_pauvre': {'nord': 'port'},
        'port': {'sud': 'quartier_pauvre', 'est': 'manoir_varlox'},
        'manoir_varlox': {'ouest': 'port'}
    }
    location_data['exits'] = exits.get(location_key, {})

    conn.close()
    return location_data

# --- Error Handling Helper ---

async def handle_save_error(interaction: discord.Interaction):
    """Sends a standardized ephemeral error message for save failures."""
    error_message = (
        "**Erreur Critique de Sauvegarde !**\n"
        "Votre progression n'a pas pu être sauvegardée. Le bot a rencontré une erreur en essayant d'écrire sur le disque.\n\n"
        "**Cause probable :** Le bot n'a pas les permissions nécessaires pour écrire dans son répertoire de données. "
        "Si vous êtes l'administrateur, veuillez vérifier les permissions du système de fichiers sur la plateforme d'hébergement."
    )
    # Use followup if the initial response was already sent
    if interaction.response.is_done():
        await interaction.followup.send(error_message, ephemeral=True)
    else:
        await interaction.response.send_message(error_message, ephemeral=True)

tensions = [
    "Un silence pesant s'installe, brusquement interrompu par le crissement de pneus non loin.",
    "Vous sentez un regard insistant sur vous, mais impossible de savoir d'où il vient.",
    "Une sirène de police retentit au loin, se rapprochant dangereusement.",
    "L'objet que vous deviez récupérer n'est pas là. À la place, il y a une simple carte, marquée d'une ombre.",
    "Votre contact est en retard. Très en retard. C'est mauvais signe.",
]

@bot.tree.command(name="start", description="Commence une aventure dans la Zilantia Moderne.")
async def start(interaction: discord.Interaction):
    """Starts the adventure for a player, placing them in their current location."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player:
        await interaction.response.send_message("Veuillez d'abord créer un personnage avec la commande `/profile`.")
        return

    location = get_location_details(player['location_key'])
    if not location:
        await interaction.response.send_message("Erreur : Votre emplacement actuel est invalide.", ephemeral=True)
        return

    message = (
        f"**Bienvenue à Zilantia, {interaction.user.mention}.**\n\n"
        f"Vous vous trouvez ici : **{location['details']['name']}**\n"
        f"{location['details']['description']}\n"
        f"{random.choice(tensions)}\n\n"
        "Que faites-vous ? Utilisez `/scan` ou `/interact` pour explorer."
    )
    await interaction.response.send_message(message)

@bot.tree.command(name="profile", description="Crée ou met à jour la fiche de votre personnage.")
async def profile(interaction: discord.Interaction, race: str, pouvoir: str):
    """Creates or updates a player's character profile in the database."""
    user_id = interaction.user.id
    user_name = interaction.user.name
    avatar_url = str(interaction.user.avatar.url)

    try:
        create_or_update_player(user_id, user_name, avatar_url, race, pouvoir)

        # Retrieve the newly created/updated profile to display it
        player = get_player(user_id)

        embed = discord.Embed(
            title=f"Fiche de Personnage de {player['user_name']}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=player['user_avatar_url'])
        embed.add_field(name="Race", value=player['race'], inline=True)
        embed.add_field(name="Pouvoir", value=player['pouvoir'], inline=True)
        embed.add_field(name="Niveau", value=player['niveau'], inline=True)
        embed.add_field(name="Traits Uniques", value=player['traits_uniques'], inline=False)
        embed.add_field(name="Artefact", value=player['artefact'], inline=False)

        await interaction.response.send_message(content="Votre profil a été créé/mis à jour !", embed=embed)

    except sqlite3.Error as e:
        print(f"Database error in /profile command: {e}")
        await interaction.response.send_message("Une erreur de base de données est survenue.", ephemeral=True)

@bot.tree.command(name="move", description="Déplacement précis dans le monde.")
async def move(interaction: discord.Interaction, direction: str):
    """Handles player movement using the database."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player or not player['location_key']:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.")
        return

    current_location = get_location_details(player['location_key'])
    direction_lower = direction.lower()

    if direction_lower in current_location.get('exits', {}):
        new_location_key = current_location['exits'][direction_lower]

        try:
            update_player_location(user_id, new_location_key)
            new_location = get_location_details(new_location_key)
            await interaction.response.send_message(
                f"Vous vous déplacez vers le **{direction}**.\n\n"
                f"Vous arrivez à **{new_location['details']['name']}**.\n"
                f"{new_location['details']['description']}"
            )
        except sqlite3.Error as e:
            print(f"Database error in /move: {e}")
            await interaction.response.send_message("Une erreur de base de données est survenue lors du déplacement.", ephemeral=True)
    else:
        possible_exits = ", ".join(current_location.get('exits', {}).keys())
        await interaction.response.send_message(f"Direction invalide. Sorties possibles : {possible_exits or 'Aucune'}")

# --- Admin Commands ---

@bot.tree.command(name="setup", description="[Admin] Lie un lieu à un canal Discord.")
@commands.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, location_key: str, channel: discord.TextChannel):
    """Links a game location to a specific Discord channel."""
    try:
        conn = get_db_connection()
        # Check if the location exists
        loc = conn.execute('SELECT 1 FROM locations WHERE key = ?', (location_key,)).fetchone()
        if not loc:
            await interaction.response.send_message(f"Erreur : Le lieu `{location_key}` n'existe pas dans la base de données.", ephemeral=True)
            conn.close()
            return

        conn.execute('UPDATE locations SET channel_id = ? WHERE key = ?', (channel.id, location_key))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Le lieu `{location_key}` a été lié au canal {channel.mention}.", ephemeral=True)

    except sqlite3.Error as e:
        print(f"Database error in /setup: {e}")
        await interaction.response.send_message("Une erreur de base de données est survenue.", ephemeral=True)

@setup.error
async def setup_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Error handler for the setup command."""
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("Vous devez être administrateur pour utiliser cette commande.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Une erreur est survenue: {error}", ephemeral=True)

# --- Player Commands ---

@bot.tree.command(name="teleport", description="Vous déplace vers un nouveau lieu et met à jour votre visibilité.")
async def teleport(interaction: discord.Interaction, destination_key: str):
    """Teleports a player to a new location, managing channel permissions."""
    user_id = interaction.user.id
    player = get_player(user_id)
    guild = interaction.guild

    if not player:
        await interaction.response.send_message("Vous devez d'abord avoir un personnage. Utilisez `/profile`.", ephemeral=True)
        return

    # Get current and destination location details from DB
    conn = get_db_connection()
    current_loc_db = conn.execute('SELECT * FROM locations WHERE key = ?', (player['location_key'],)).fetchone()
    destination_loc_db = conn.execute('SELECT * FROM locations WHERE key = ?', (destination_key,)).fetchone()
    conn.close()

    if not destination_loc_db:
        await interaction.response.send_message(f"Destination `{destination_key}` invalide.", ephemeral=True)
        return

    if current_loc_db['key'] == destination_loc_db['key']:
        await interaction.response.send_message(f"Vous êtes déjà à `{destination_loc_db['name']}`.", ephemeral=True)
        return

    # Check if channels have been set up
    if not current_loc_db['channel_id'] or not destination_loc_db['channel_id']:
        await interaction.response.send_message("Erreur de configuration : les canaux pour les lieux actuels ou de destination ne sont pas définis. Un admin doit utiliser `/setup`.", ephemeral=True)
        return

    # Get channel objects
    try:
        current_channel = guild.get_channel(current_loc_db['channel_id'])
        destination_channel = guild.get_channel(destination_loc_db['channel_id'])
        if not current_channel or not destination_channel:
            raise AttributeError # If a channel was deleted
    except AttributeError:
        await interaction.response.send_message("Erreur : Un des canaux configurés n'existe plus sur ce serveur.", ephemeral=True)
        return

    # Update database first
    try:
        update_player_location(user_id, destination_key)
    except sqlite3.Error as e:
        print(f"Database error in /teleport: {e}")
        await interaction.response.send_message("Erreur de base de données lors de la téléportation.", ephemeral=True)
        return

    # Manage channel permissions
    try:
        await current_channel.set_permissions(interaction.user, read_messages=False)
        await destination_channel.set_permissions(interaction.user, read_messages=True)
    except discord.Forbidden:
        await interaction.response.send_message("Erreur : Le bot n'a pas les permissions nécessaires pour gérer les canaux. Veuillez vérifier ses rôles.", ephemeral=True)
        # Revert location change in DB
        update_player_location(user_id, current_loc_db['key'])
        return

    await interaction.response.send_message(f"Téléportation réussie ! Vous êtes maintenant à **{destination_loc_db['name']}**. Le canal {destination_channel.mention} est maintenant visible.")


@bot.tree.command(name="scan", description="Analyse la zone.")
async def scan(interaction: discord.Interaction):
    """Scans the current area using data from the database."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player or not player['location_key']:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.")
        return

    location = get_location_details(player['location_key'])

    embed = discord.Embed(
        title=f"Scan de : {location['details']['name']}",
        description=location['details']['description'],
        color=discord.Color.green()
    )

    if location['pnjs']:
        pnj_list = "\n".join([f"- {pnj['name']}: {pnj['description']}" for pnj in location['pnjs']])
        embed.add_field(name="PNJs présents", value=pnj_list, inline=False)

    if location['items']:
        item_list = "\n".join([f"- {item['name']}: {item['description']}" for item in location['items']])
        embed.add_field(name="Objets notables", value=item_list, inline=False)

    if location['enemies']:
        enemy_list = "\n".join([f"- {enemy['name']}" for enemy in location['enemies']])
        embed.add_field(name="Ennemis", value=enemy_list, inline=False)

    if not location['pnjs'] and not location['items'] and not location['enemies']:
        embed.add_field(name="Résultat du scan", value="La zone semble calme. Rien à signaler.", inline=False)

    await interaction.response.send_message(embed=embed)

# --- Combat System ---
# This can be removed or refactored later, as combat state is not persistent yet
active_combats = {}

# The rest of the combat system (CombatView) would need a larger refactor
# to work with the database, so we will simplify it for now.
# A full implementation would involve storing combat state in the DB.

@bot.tree.command(name="fight", description="Engage un combat (simplifié).")
async def fight(interaction: discord.Interaction):
    """A simplified combat command."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player or not player['location_key']:
        await interaction.response.send_message("Vous devez d'abord avoir un personnage et être dans le monde. Utilisez `/profile` et `/start`.")
        return

    location = get_location_details(player['location_key'])

    if not location['enemies']:
        await interaction.response.send_message("Il n'y a personne à combattre ici.")
        return

    # Simplified combat: win/loss based on a random roll
    enemy = location['enemies'][0]
    await interaction.response.send_message(f"Vous engagez le combat avec **{enemy['name']}** !")

    # Simulate a fight
    player_win = random.choice([True, False])

    if player_win:
        conn = get_db_connection()
        conn.execute('DELETE FROM enemies WHERE id = ?', (enemy['id'],))
        conn.commit()
        conn.close()
        await interaction.followup.send(f"Après un combat acharné, vous avez vaincu **{enemy['name']}** !")
    else:
        await interaction.followup.send(f"**{enemy['name']}** vous a vaincu ! Vous battez en retraite pour panser vos plaies.")

# --- AI Text Generation ---

def generate_text_response(prompt, system_prompt):
    """Generates a text response using the Pollinations.ai API."""
    url = "https://text.pollinations.ai"
    try:
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "model": "openai", # Although it says openai, it's their free model
            "seed": random.randint(1, 999999999),
        }
        response = requests.post(url, json=data, timeout=15) # Add a 15-second timeout
        response.raise_for_status() # Raise an exception for bad status codes
        # The API returns a JSON object where the response is in 'choices'[0]['message']['content']
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        print("API Error: Request to Pollinations text API timed out.")
        return "Le service IA a mis trop de temps à répondre. Il est peut-être surchargé. Veuillez réessayer."
    except requests.exceptions.RequestException as e:
        print(f"API Error: Failed to connect to Pollinations text API: {e}")
        return "Impossible de contacter le service IA. Il est peut-être temporairement hors ligne."
    except (KeyError, IndexError) as e:
        print(f"API Error: Invalid response format from Pollinations text API: {e}")
        print(f"Full response: {response.text if 'response' in locals() else 'No response object'}")
        return "Le service IA a renvoyé une réponse inattendue. Veuillez réessayer."

# --- AI Image Generation ---

@bot.tree.command(name="image", description="Génère une image d'ambiance de Zilantia.")
async def image(interaction: discord.Interaction, prompt: str):
    """Generates an image using the Pollinations.ai API."""
    await interaction.response.defer()

    try:
        # A safe prompt prefix to guide the AI towards the desired style
        full_prompt = f"cyberpunk noir, city of zilantia, {prompt}, cinematic, photorealistic, 4k"
        image_url = f"https://image.pollinations.ai/prompt/{full_prompt}"

        # Check if the image was generated successfully
        # Use a short timeout as we are just checking headers
        response = requests.head(image_url, timeout=10)
        response.raise_for_status()

        # We don't need to download the image, Discord can embed directly from a URL
        embed = discord.Embed(
            title="Image de Zilantia",
            description=f"Prompt : `{prompt}`",
            color=discord.Color.purple()
        )
        embed.set_image(url=image_url)
        embed.set_footer(text="Généré avec Pollinations.ai")

        await interaction.followup.send(embed=embed)

    except requests.exceptions.Timeout:
        print("API Error: Request to Pollinations image API timed out.")
        await interaction.followup.send("Le service de génération d'images a mis trop de temps à répondre. Il est peut-être surchargé.", ephemeral=True)
    except requests.exceptions.RequestException as e:
        print(f"API Error: Failed to connect to Pollinations image API: {e}")
        await interaction.followup.send("Impossible de contacter le service de génération d'images. Il est peut-être temporairement hors ligne.", ephemeral=True)


@bot.tree.command(name="interact", description="Interagir avec un PNJ ou un objet.")
async def interact(interaction: discord.Interaction, target: str, message: str = "Je m'approche et j'observe."):
    """Interacts with a target using data from the database."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player or not player['location_key']:
        await interaction.response.send_message("Vous devez d'abord avoir un personnage. Utilisez `/profile`.", ephemeral=True)
        return

    location = get_location_details(player['location_key'])
    target_lower = target.lower()

    # --- PNJ Interaction ---
    for pnj in location['pnjs']:
        if pnj['name'].lower() == target_lower:
            await interaction.response.defer()
            ai_response = generate_text_response(message, pnj['system_prompt'])
            await interaction.followup.send(f"**{pnj['name']}**: \"{ai_response}\"")
            return

    # --- Item Interaction ---
    for item in location['items']:
        if item['name'].lower() == target_lower:
            await interaction.response.send_message(f"Vous examinez **{item['name']}**: {item['description']}")
            return

    await interaction.response.send_message(f"Impossible de trouver '{target}' ici.", ephemeral=True)

@bot.tree.command(name="portal", description="Tente d'ouvrir une brèche dimensionnelle.")
async def portal(interaction: discord.Interaction):
    """Attempts to open a portal."""
    await interaction.response.send_message("Vous essayez d'ouvrir un portail, mais rien ne se passe. Peut-être que le pouvoir vous manque...")

def get_player_mission(user_id):
    """Retrieves a player's active mission."""
    conn = get_db_connection()
    mission = conn.execute('SELECT * FROM player_missions WHERE player_user_id = ? AND status = "accepted"', (user_id,)).fetchone()
    conn.close()
    return mission

def get_mission_details(mission_id):
    """Retrieves details for a specific mission."""
    conn = get_db_connection()
    mission = conn.execute('SELECT * FROM missions WHERE id = ?', (mission_id,)).fetchone()
    conn.close()
    return mission

def start_player_mission(user_id, mission_id):
    """Assigns a mission to a player."""
    conn = get_db_connection()
    conn.execute('INSERT INTO player_missions (player_user_id, mission_id, status, progress) VALUES (?, ?, "accepted", "{}")', (user_id, mission_id))
    conn.commit()
    conn.close()

class MissionAcceptView(discord.ui.View):
    def __init__(self, missions, user_id):
        super().__init__(timeout=180.0)
        self.user_id = user_id

        # Add a select menu with the available missions
        options = [discord.SelectOption(label=m['name'], value=m['id'], description=m['description'][:100]) for m in missions]
        self.select_menu = discord.ui.Select(placeholder="Choisissez une mission...", options=options)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ce n'est pas votre menu !", ephemeral=True)
            return

        mission_id = self.select_menu.values[0]
        try:
            start_player_mission(self.user_id, mission_id)
            mission_details = get_mission_details(mission_id)
            await interaction.response.edit_message(content=f"**Mission acceptée : {mission_details['name']}**\n> {mission_details['description']}", view=None)
        except sqlite3.IntegrityError:
             await interaction.response.edit_message(content="Vous avez déjà accepté cette mission ou une autre.", view=None)
        except Exception as e:
            print(f"Error in mission selection: {e}")
            await interaction.response.edit_message(content="Une erreur est survenue.", view=None)

@bot.tree.command(name="mission", description="Consulte ou accepte une mission.")
async def mission(interaction: discord.Interaction):
    """Lists and manages missions from the database."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player:
        await interaction.response.send_message("Veuillez d'abord créer un profil avec `/profile`.", ephemeral=True)
        return

    # Check for active mission
    active_mission = get_player_mission(user_id)
    if active_mission:
        mission_details = get_mission_details(active_mission['mission_id'])
        await interaction.response.send_message(f"**Mission en cours : {mission_details['name']}**\n> {mission_details['description']}")
        return

    # List available missions in the current location
    conn = get_db_connection()
    available_missions = conn.execute('SELECT * FROM missions WHERE start_location_key = ?', (player['location_key'],)).fetchall()
    conn.close()

    if not available_missions:
        await interaction.response.send_message("Aucune mission disponible ici pour le moment.")
        return

    view = MissionAcceptView(available_missions, user_id)
    await interaction.response.send_message("Missions disponibles dans cette zone :", view=view)

@bot.tree.command(name="event", description="Lance un évènement aléatoire.")
async def event(interaction: discord.Interaction):
    """Triggers a random event."""
    events = [
        "Une voiture noire aux vitres teintées vous suit depuis plusieurs rues.",
        "Vous entendez une explosion au loin. La fumée s'élève dans le ciel nocturne.",
        "Un PNJ inconnu vous bouscule et glisse un objet dans votre poche. Qu'est-ce que c'est ?",
    ]
    await interaction.response.send_message(f"Événement aléatoire : {random.choice(events)}")


if __name__ == "__main__":
    # The database is now the single source of truth, so we don't need to load files on startup.
    # We just need to ensure the DB file exists.
    if not os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' not found. Please run `python3 database_setup.py` first.")
        exit()

    if TOKEN is None:
        print("Error: DISCORD_TOKEN environment variable not set.")
        print("Please create a .env file and add your token, e.g., DISCORD_TOKEN=your_token_here")
    else:
        bot.run(TOKEN)
