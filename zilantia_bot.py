import discord
from discord.ext import commands
from discord import ui
import os
import random
import json
import requests
import sqlite3
import re
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

# --- Database Connection ---

DB_FILE = 'zilantia.db'

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- AI Prompt Generation ---

def _create_interaction_prompt(pnj_name: str, pnj_personality: str, player_profile: dict, interaction_message: str) -> str:
    """Creates the detailed system prompt for the AI to generate PNJ dialogue."""
    return (
        f"**Rôle :** Tu es un PNJ expert en jeu de rôle textuel dans un univers GTA-like avec des pouvoirs magiques. "
        f"Tu incarnes '{pnj_name}'.\n"
        f"**Personnalité de {pnj_name} :** {pnj_personality}\n"
        f"**Contexte :** Le joueur '{player_profile['user_name']}' (Race: {player_profile['race']}, Pouvoir: {player_profile['pouvoir']}) vient d'interagir avec toi en disant : \"{interaction_message}\".\n"
        f"**Instructions :**\n"
        f"1.  **Réponds de manière immersive et concise (2-3 phrases maximum).**\n"
        f"2.  **Reste fidèle à la personnalité de {pnj_name}.** Ne sois jamais un simple assistant IA.\n"
        f"3.  **Fais avancer l'interaction.** Pose une question, donne un indice subtil ou provoque une réaction.\n"
        f"4.  **Ne parle jamais à la place du joueur.**\n"
        f"**Exemple de bonne réponse (si le PNJ est un barman bourru) :** "
        f"\"'Un autre ? T'as l'air de quelqu'un qui cherche les ennuis. Qu'est-ce que tu veux vraiment ?\""
    )

# --- Data Access Functions ---

def get_player(user_id: int) -> sqlite3.Row | None:
    """
    Retrieves a single player's complete profile from the database.

    Args:
        user_id: The Discord user ID of the player.

    Returns:
        A sqlite3.Row object representing the player, or None if not found.
    """
    conn = get_db_connection()
    player = conn.execute('SELECT * FROM players WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return player

def create_or_update_player(user_id: int, user_name: str, avatar_url: str, race: str, pouvoir: str):
    """
    Creates a new player record or updates the core details of an existing one.
    Uses INSERT ON CONFLICT to handle both cases in a single, atomic database operation.
    New players are automatically placed in 'quartier_pauvre'.
    """
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

def update_player_location(user_id: int, new_location_key: str):
    """
    Updates only the player's current location key in the database.

    Args:
        user_id: The Discord user ID of the player to update.
        new_location_key: The key of the new location (e.g., 'port', 'manoir_varlox').
    """
    conn = get_db_connection()
    conn.execute('UPDATE players SET location_key = ? WHERE user_id = ?', (new_location_key, user_id))
    conn.commit()
    conn.close()

def get_location_details(location_key: str) -> dict | None:
    """
    Retrieves full details for a given location key.
    This includes the location's description, as well as all associated PNJs,
    items, and enemies by querying related tables.
    """
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

    # Fetch exits from the database
    exits_rows = conn.execute('SELECT direction, destination_location_key FROM location_exits WHERE source_location_key = ?', (location_key,)).fetchall()
    location_data['exits'] = {row['direction']: row['destination_location_key'] for row in exits_rows}

    conn.close()
    return location_data


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

def start_combat(user_id, enemy_id, enemy_health):
    """Initiates a combat in the database."""
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO active_combats (player_user_id, enemy_id, enemy_current_health) VALUES (?, ?, ?)', (user_id, enemy_id, enemy_health))
    conn.commit()
    conn.close()

@bot.tree.command(name="fight", description="Engage le combat avec une cible.")
async def fight(interaction: discord.Interaction, target: str):
    """Initiates combat with a specified enemy."""
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player or not player['location_key']:
        await interaction.response.send_message("Vous devez avoir un personnage pour combattre. Utilisez `/profile` et `/start`.", ephemeral=True)
        return

    # Check if already in combat
    if get_combat_state(user_id):
        await interaction.response.send_message("Vous êtes déjà en combat ! Utilisez `/action` pour continuer.", ephemeral=True)
        return

    location = get_location_details(player['location_key'])
    target_lower = target.lower()

    for enemy in location['enemies']:
        if enemy['name'].lower() == target_lower:
            try:
                start_combat(user_id, enemy['id'], enemy['health'])
                await interaction.response.send_message(f"Vous engagez le combat avec **{enemy['name']}** ! Utilisez la commande `/action` pour décrire ce que vous faites.")
                return
            except sqlite3.Error as e:
                print(f"Database error in /fight: {e}")
                await interaction.response.send_message("Une erreur de base de données est survenue en tentant de commencer le combat.", ephemeral=True)
                return

    await interaction.response.send_message(f"Impossible de trouver un ennemi nommé '{target}' ici.", ephemeral=True)

@bot.tree.command(name="action", description="Effectue une action pendant un combat.")
async def action(interaction: discord.Interaction, votre_action: str):
    """
    Handles a player's action during combat.
    It generates a narrative from the AI, parses structured damage values,
    updates health for both player and enemy, and checks for victory or defeat.
    """
    user_id = interaction.user.id
    player = get_player(user_id)

    if not player:
        await interaction.response.send_message("Vous devez avoir un personnage pour agir. Utilisez `/profile`.", ephemeral=True)
        return

    combat_state = get_combat_state(user_id)
    if not combat_state:
        await interaction.response.send_message("Vous n'êtes pas en combat. Utilisez `/fight` pour en commencer un.", ephemeral=True)
        return

    await interaction.response.defer()

    # Generate the full response from the AI
    ai_response = generate_combat_narrative(player, combat_state, votre_action)

    # --- Parse Narrative and Structured Damage ---
    narrative = ai_response
    player_damage = 0
    enemy_damage = 0

    # Use regex to find the structured damage lines and separate them from the narrative
    player_damage_match = re.search(r'PLAYER_DAMAGE:\s*(\d+)', ai_response)
    if player_damage_match:
        player_damage = int(player_damage_match.group(1))
        narrative = narrative.replace(player_damage_match.group(0), '').strip()

    enemy_damage_match = re.search(r'ENEMY_DAMAGE:\s*(\d+)', ai_response)
    if enemy_damage_match:
        enemy_damage = int(enemy_damage_match.group(1))
        narrative = narrative.replace(enemy_damage_match.group(0), '').strip()

    # --- Update Health States ---
    new_player_health = player['health'] - player_damage
    new_enemy_health = combat_state['enemy_current_health'] - enemy_damage

    # --- Construct the Final Message ---
    final_message = (
        f"**{player['user_name']}**: `{votre_action}`\n\n"
        f"{narrative}\n\n"
        f"--- **État du Combat** ---\n"
        f"❤️ **{player['user_name']}**: {new_player_health}/100 PV\n"
        f"💀 **{combat_state['name']}**: {new_enemy_health}/{combat_state['max_health']} PV"
    )

    # --- Check for Victory/Defeat ---
    if new_player_health <= 0:
        end_combat(user_id)
        update_player_health(user_id, 1) # Revive with 1 HP
        final_message += "\n\n**☠️ Vous avez été vaincu...** Vous vous réveillez plus tard, affaibli mais en vie."
    elif new_enemy_health <= 0:
        end_combat(user_id)
        final_message += f"\n\n**🎉 Vous avez vaincu {combat_state['name']} !**"
    else:
        # If the fight continues, update health in the database
        update_player_health(user_id, new_player_health)
        update_combat_state(user_id, combat_state['enemy_id'], new_enemy_health)

    await interaction.followup.send(final_message)

# --- Data Access Functions for Combat ---

def get_combat_state(user_id):
    """Retrieves the current combat state for a player."""
    conn = get_db_connection()
    combat_state = conn.execute('''
        SELECT
            ac.enemy_id,
            ac.enemy_current_health,
            e.name,
            e.damage,
            e.health as max_health
        FROM active_combats ac
        JOIN enemies e ON ac.enemy_id = e.id
        WHERE ac.player_user_id = ?
    ''', (user_id,)).fetchone()
    conn.close()
    return combat_state

def update_combat_state(user_id, enemy_id, new_health):
    """Updates the health of an enemy in combat."""
    conn = get_db_connection()
    conn.execute('UPDATE active_combats SET enemy_current_health = ? WHERE player_user_id = ? AND enemy_id = ?', (new_health, user_id, enemy_id))
    conn.commit()
    conn.close()

def update_player_health(user_id: int, new_health: int):
    """
    Updates a player's health in the main players table.
    """
    conn = get_db_connection()
    conn.execute('UPDATE players SET health = ? WHERE user_id = ?', (new_health, user_id))
    conn.commit()
    conn.close()

def end_combat(user_id):
    """Removes a player's combat state from the database."""
    conn = get_db_connection()
    conn.execute('DELETE FROM active_combats WHERE player_user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# --- AI Text Generation ---

def generate_combat_narrative(player, combat_state, player_action):
    """Generates a combat narrative using a detailed contextual prompt."""

    system_prompt = f"""
    **Rôle :** Tu es un Maître du Jeu (MJ) expert en RPG textuel pour l'univers cyberpunk noir de Zilantia. Ta tâche est de narrer les tours de combat de manière immersive et de calculer les dégâts.

    **Contexte du Combat :**
    *   **Joueur :** {player['user_name']}
        *   Santé : {player['health']}/100
        *   Pouvoir : {player['pouvoir']}
    *   **Ennemi :** {combat_state['name']}
        *   Santé : {combat_state['enemy_current_health']}
        *   Attaque de base : {combat_state['damage']} de dégâts

    **Action du Joueur :** "{player_action}"

    **Instructions :**
    1.  **Narrer l'Action :** Décris l'action du joueur et la réaction de l'ennemi de manière vivante et concise (2-3 phrases).
    2.  **Calculer les Dégâts de l'Ennemi :** L'ennemi attaque toujours en retour. Calcule ses dégâts en te basant sur son attaque de base ({combat_state['damage']}).
    3.  **Calculer les Dégâts du Joueur :** Évalue l'action du joueur. Un coup simple fait environ 5-10 dégâts. Une utilisation créative de son pouvoir ('{player['pouvoir']}') peut faire entre 15 et 25 dégâts.
    4.  **Format de Sortie Obligatoire :** Termine TOUJOURS ta réponse par les deux lignes suivantes, sans texte supplémentaire après :
        `PLAYER_DAMAGE: [nombre de dégâts subis par le joueur]`
        `ENEMY_DAMAGE: [nombre de dégâts subis par l'ennemi]`

    **Exemple de réponse :**
    *L'ombre lancée par {player['user_name']} frappe l'homme de main en pleine poitrine, le faisant reculer. Avant qu'il ne puisse récupérer, l'ennemi tire une rafale avec son pistolet, vous touchant à l'épaule.*
    *PLAYER_DAMAGE: 8*
    *ENEMY_DAMAGE: 17*
    """

    # The user's action is sent as the main prompt, the system prompt provides all the rules.
    return generate_text_response(player_action, system_prompt)


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

            # The 'system_prompt' column in the DB holds the PNJ's core personality.
            pnj_personality = pnj['system_prompt']

            # Create the full, contextual prompt using the new helper function.
            full_prompt = _create_interaction_prompt(
                pnj_name=pnj['name'],
                pnj_personality=pnj_personality,
                player_profile=player,
                interaction_message=message
            )

            # The user's message is already part of the system prompt for context,
            # but we also send it as the main prompt to the AI.
            ai_response = generate_text_response(message, full_prompt)
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
