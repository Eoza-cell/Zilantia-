import discord
from discord.ext import commands
from discord import ui
import os
import random
import json
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
    def __init__(self, name, description, dialogue):
        self.name = name
        self.description = description
        self.dialogue = dialogue
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

# --- Player Data ---
PLAYER_DATA_FILE = "player_data.json"
player_profiles = {}

def save_player_data():
    """
    Saves the player profiles to a JSON file.
    Returns True on success, False on failure.
    """
    try:
        data_to_save = {user_id: player.to_dict() for user_id, player in player_profiles.items()}
        with open(PLAYER_DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        return True
    except (IOError, OSError) as e:
        print(f"!!! CRITICAL ERROR: Failed to save player data to {PLAYER_DATA_FILE} !!!")
        print(f"Error details: {e}")
        print("This is likely due to a file permissions issue in the deployment environment.")
        return False

def load_player_data():
    """Loads player profiles from a JSON file."""
    global player_profiles
    try:
        with open(PLAYER_DATA_FILE, 'r') as f:
            data = json.load(f)
            player_profiles = {int(user_id): Player.from_dict(p_data) for user_id, p_data in data.items()}
    except FileNotFoundError:
        player_profiles = {} # No data file yet

# --- World Data ---
WORLD_DATA_FILE = "world_data.json"
world_locations = {}

def save_world_data():
    """
    Saves the world state to a JSON file.
    Returns True on success, False on failure.
    """
    try:
        data_to_save = {key: loc.to_dict() for key, loc in world_locations.items()}
        with open(WORLD_DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        return True
    except (IOError, OSError) as e:
        print(f"!!! CRITICAL ERROR: Failed to save world data to {WORLD_DATA_FILE} !!!")
        print(f"Error details: {e}")
        print("This is likely due to a file permissions issue in the deployment environment.")
        return False

def load_world_data():
    """Loads the world state from a JSON file, creating it if it doesn't exist."""
    global world_locations
    try:
        with open(WORLD_DATA_FILE, 'r') as f:
            data = json.load(f)
            for key, loc_data in data.items():
                world_locations[key] = Location(
                    name=loc_data["name"],
                    description=loc_data["description"],
                    pnjs=[PNJ(**pnj_data) for pnj_data in loc_data.get("pnjs", [])],
                    items=[Item(**item_data) for item_data in loc_data.get("items", [])],
                    exits=loc_data.get("exits", {}),
                    enemies=[Enemy(**enemy_data) for enemy_data in loc_data.get("enemies", [])]
                )
    except FileNotFoundError:
        print("World data file not found, creating a new one with Zilantia GTA theme.")
        world_locations = {
            "quartier_pauvre": Location(
                name="Quartier Pauvre",
                description="Un dédale de ruelles humides et de bâtiments délabrés. L'odeur de la pauvreté et du désespoir est palpable.",
                pnjs=[PNJ("Vieux Leo", "Un vieil homme assis sur un carton, il a tout vu.", "Le Syndicat Noir... ils sont les rois ici. Fais attention à toi.")],
                items=[Item("Colis suspect", "Une caisse en bois qui vibre légèrement. Prêt pour la mission `/mission`?")],
                exits={"nord": "port"}
            ),
            "port": Location(
                name="Le Port de Zilantia",
                description="Des grues rouillées se dressent vers le ciel. Les conteneurs sont une cachette parfaite pour les trafics.",
                pnjs=[PNJ("Contact de l'Ombre", "Un homme au visage dissimulé.", "Vous avez la livraison ?")],
                enemies=[Enemy("Homme de main du Syndicat", 40, 8)],
                exits={"sud": "quartier_pauvre", "est": "manoir_varlox"}
            ),
            "manoir_varlox": Location(
                name="Manoir de Varlox",
                description="Une immense bâtisse sombre qui surplombe la ville. Les ombres semblent danser sur ses murs.",
                pnjs=[PNJ("Don Varlox", "Le Roi des Ombres, assis sur un trône d'obsidienne.", "Alors, une nouvelle souris est entrée dans mon royaume...")],
                exits={"ouest": "port"}
            )
        }
        save_world_data()

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
    """Generates a starting scenario for the player."""
    user_id = interaction.user.id
    if user_id not in player_profiles:
        await interaction.response.send_message("Veuillez d'abord créer un personnage avec la commande `/profile`.")
        return

    player = player_profiles[user_id]

    # Randomly select a starting location
    start_location_key = random.choice(list(world_locations.keys()))
    player.location_key = start_location_key
    if not save_player_data():
        await handle_save_error(interaction)
        return

    # Create the introductory message
    location = world_locations[player.location_key]
    message = (
        f"**Bienvenue à Zilantia, {interaction.user.mention}.**\n\n"
        f"Vous vous trouvez ici : **{location.name}**\n"
        f"{location.description}\n"
        f"{random.choice(tensions)}\n\n"
        "Que faites-vous ? Utilisez `/scan` ou `/interact` pour explorer."
    )

    await interaction.response.send_message(message)

class ConfirmOverwriteView(ui.View):
    def __init__(self, user_id, race, pouvoir):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        self.race = race
        self.pouvoir = pouvoir

    @ui.button(label="Oui", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        embed, success = create_profile(interaction, self.user_id, self.race, self.pouvoir, overwrite=True)
        if success:
            await interaction.response.edit_message(content="Votre ancien profil a été écrasé. Voici votre nouvelle fiche :", embed=embed, view=None)
        else:
            await interaction.response.edit_message(content="La création du profil a échoué en raison d'une erreur de sauvegarde.", view=None)
            await handle_save_error(interaction)
        self.stop()

    @ui.button(label="Non", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Opération annulée.", ephemeral=True)
        self.stop()

def create_profile(interaction, user_id, race, pouvoir, overwrite=False):
    """
    Helper function to create or overwrite a profile.
    Returns a tuple of (embed, success_boolean).
    """
    player = Player(
        user_id=user_id,
        user_name=interaction.user.name,
        user_avatar_url=str(interaction.user.avatar.url),
        race=race,
        pouvoir=pouvoir
    )
    player_profiles[user_id] = player
    success = save_player_data()

    embed = discord.Embed(
        title=f"Fiche de Personnage de {player.user_name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=player.user_avatar_url)
    embed.add_field(name="Race", value=player.race, inline=True)
    embed.add_field(name="Pouvoir", value=player.pouvoir, inline=True)
    embed.add_field(name="Niveau", value=player.niveau, inline=True)
    embed.add_field(name="Traits Uniques", value=player.traits_uniques, inline=False)
    embed.add_field(name="Artefact", value=player.artefact, inline=False)

    return embed, success

@bot.tree.command(name="profile", description="Crée ou met à jour la fiche de votre personnage.")
async def profile(interaction: discord.Interaction, race: str, pouvoir: str):
    """Creates or updates a player's character profile."""
    user_id = interaction.user.id

    if user_id in player_profiles:
        view = ConfirmOverwriteView(user_id, race, pouvoir)
        await interaction.response.send_message(
            "Un profil existe déjà pour vous. Voulez-vous l'écraser ? Votre progression sera perdue.",
            view=view,
            ephemeral=True
        )
    else:
        embed, success = create_profile(interaction, user_id, race, pouvoir)
        if success:
            await interaction.response.send_message(embed=embed)
        else:
            await handle_save_error(interaction)

@bot.tree.command(name="move", description="Déplacement précis dans le monde.")
async def move(interaction: discord.Interaction, direction: str):
    """Handles player movement."""
    user_id = interaction.user.id
    if user_id not in player_profiles or player_profiles[user_id].location_key is None:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.")
        return

    player = player_profiles[user_id]
    current_location = world_locations[player.location_key]
    direction_lower = direction.lower()

    if direction_lower in current_location.exits:
        new_location_key = current_location.exits[direction_lower]
        current_location_key = player.location_key # Backup
        player.location_key = new_location_key

        if not save_player_data():
            await handle_save_error(interaction)
            # Restore previous location to prevent inconsistent state
            player.location_key = current_location_key
            return

        new_location = world_locations[new_location_key]
        await interaction.response.send_message(
            f"Vous vous déplacez vers le **{direction}**.\n\n"
            f"Vous arrivez à **{new_location.name}**.\n"
            f"{new_location.description}"
        )
    else:
        possible_exits = ", ".join(current_location.exits.keys())
        await interaction.response.send_message(f"Direction invalide. Sorties possibles : {possible_exits}")

@bot.tree.command(name="scan", description="Analyse la zone.")
async def scan(interaction: discord.Interaction):
    """Scans the current area."""
    user_id = interaction.user.id
    if user_id not in player_profiles or player_profiles[user_id].location_key is None:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.")
        return

    player = player_profiles[user_id]
    location = world_locations[player.location_key]

    embed = discord.Embed(
        title=f"Scan de : {location.name}",
        description=location.description,
        color=discord.Color.green()
    )

    if location.pnjs:
        pnj_list = "\n".join([f"- {pnj.name}: {pnj.description}" for pnj in location.pnjs])
        embed.add_field(name="PNJs présents", value=pnj_list, inline=False)

    if location.items:
        item_list = "\n".join([f"- {item.name}: {item.description}" for item in location.items])
        embed.add_field(name="Objets notables", value=item_list, inline=False)

    if not location.pnjs and not location.items:
        embed.add_field(name="Résultat du scan", value="La zone semble calme. Rien à signaler.", inline=False)

    await interaction.response.send_message(embed=embed)

# --- Combat System ---
active_combats = {}

class CombatView(ui.View):
    def __init__(self, player, enemy, original_interaction):
        super().__init__(timeout=180.0)
        self.player = player
        self.enemy = enemy
        self.original_interaction = original_interaction
        self.combat_log = ""

    async def update_interaction(self, interaction: discord.Interaction):
        """Helper to update the combat message."""
        if self.player.health <= 0 or self.enemy.health <= 0:
            self.disable_all_items()
            if self.player.health <= 0:
                self.combat_log += "\n**Vous avez été vaincu...**"
                self.player.health = 100 # Reset health
            else:
                self.combat_log += f"\n**Vous avez vaincu {self.enemy.name} !**"
                # Remove enemy from the world
                location = world_locations[self.player.location_key]
                if location.enemies: # Avoid crash if enemy list is already empty
                    location.enemies.pop(0)
                    if not save_world_data():
                        await handle_save_error(interaction)

            del active_combats[self.player.user_id]
            if not save_player_data():
                 await handle_save_error(interaction)

        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        embed = discord.Embed(title=f"Combat: {self.player.user_name} vs. {self.enemy.name}", color=discord.Color.red())
        embed.add_field(name="Votre Santé", value=f"{self.player.health}/100", inline=True)
        embed.add_field(name=f"Santé de {self.enemy.name}", value=f"{self.enemy.health}", inline=True)
        embed.add_field(name="Log de Combat", value=self.combat_log or "Le combat commence !", inline=False)
        return embed

    def enemy_turn(self):
        """The enemy's action."""
        self.player.health -= self.enemy.damage
        self.combat_log += f"\n{self.enemy.name} vous attaque et vous inflige {self.enemy.damage} points de dégâts."

    @ui.button(label="Attaquer", style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, button: ui.Button):
        player_damage = random.randint(10, 20)
        self.enemy.health -= player_damage
        self.combat_log = f"Vous attaquez {self.enemy.name} et lui infligez {player_damage} points de dégâts."
        if self.enemy.health > 0:
            self.enemy_turn()
        await self.update_interaction(interaction)

    @ui.button(label="Esquiver", style=discord.ButtonStyle.secondary)
    async def dodge(self, interaction: discord.Interaction, button: ui.Button):
        dodged = random.choice([True, False])
        if dodged:
            self.combat_log = "Vous esquivez l'attaque de l'ennemi !"
        else:
            self.combat_log = "Vous n'avez pas réussi à esquiver."
            self.enemy_turn()
        await self.update_interaction(interaction)

    @ui.button(label="Pouvoir", style=discord.ButtonStyle.primary)
    async def power(self, interaction: discord.Interaction, button: ui.Button):
        power_damage = random.randint(20, 30) # Powers are stronger
        self.enemy.health -= power_damage
        self.combat_log = f"Vous utilisez votre pouvoir sur {self.enemy.name} pour {power_damage} points de dégâts !"
        if self.enemy.health > 0:
            self.enemy_turn()
        await self.update_interaction(interaction)


@bot.tree.command(name="fight", description="Active le mode combat.")
async def fight(interaction: discord.Interaction):
    """Activates combat mode."""
    user_id = interaction.user.id
    if user_id in active_combats:
        await interaction.response.send_message("Vous êtes déjà en combat.", ephemeral=True)
        return

    if user_id not in player_profiles or player_profiles[user_id].location_key is None:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.", ephemeral=True)
        return

    player = player_profiles[user_id]
    location = world_locations[player.location_key]

    if not location.enemies:
        await interaction.response.send_message("Il n'y a personne à combattre ici.", ephemeral=True)
        return

    enemy = location.enemies[0]
    active_combats[user_id] = True

    view = CombatView(player=player, enemy=enemy, original_interaction=interaction)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="interact", description="Interagir avec un PNJ ou un objet.")
async def interact(interaction: discord.Interaction, target: str):
    """Interacts with a target, potentially for a mission."""
    user_id = interaction.user.id
    if user_id not in player_profiles or player_profiles[user_id].location_key is None:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.", ephemeral=True)
        return

    player = player_profiles[user_id]
    location = world_locations[player.location_key]
    target_lower = target.lower()

    # Mission Interaction Logic
    if player.active_mission_id:
        mission = available_missions[player.active_mission_id]

        # Start objective interaction
        if not player.mission_progress.get("package_collected") and mission.start_objective["target"].lower() == target_lower:
            player.mission_progress["package_collected"] = True
            if save_player_data():
                await interaction.response.send_message(f"Vous avez récupéré le **{target}**. Vous devriez maintenant l'apporter au contact sur le Port.")
            else:
                player.mission_progress["package_collected"] = False # Revert state
                await handle_save_error(interaction)
            return

        # End objective interaction
        if player.mission_progress.get("package_collected") and mission.end_objective["target"].lower() == target_lower:
            # Stash state in case of save failure
            previous_mission_id = player.active_mission_id
            previous_progress = player.mission_progress.copy()

            player.active_mission_id = None
            player.mission_progress = {}

            if save_player_data():
                await interaction.response.send_message(f"Mission **{mission.name}** terminée ! Le contact vous remercie d'un signe de tête et disparaît.")
            else:
                # Revert state
                player.active_mission_id = previous_mission_id
                player.mission_progress = previous_progress
                await handle_save_error(interaction)
            return

    # Regular Interaction Logic
    for pnj in location.pnjs:
        if pnj.name.lower() == target_lower:
            await interaction.response.send_message(f"**{pnj.name}**: \"{pnj.dialogue}\"")
            return

    for item in location.items:
        if item.name.lower() == target_lower:
            await interaction.response.send_message(f"Vous examinez **{item.name}**: {item.description}")
            return

    await interaction.response.send_message(f"Impossible de trouver '{target}' ici.", ephemeral=True)

@bot.tree.command(name="portal", description="Tente d'ouvrir une brèche dimensionnelle.")
async def portal(interaction: discord.Interaction):
    """Attempts to open a portal."""
    await interaction.response.send_message("Vous essayez d'ouvrir un portail, mais rien ne se passe. Peut-être que le pouvoir vous manque...")

@bot.tree.command(name="mission", description="Accepte ou consulte une mission.")
async def mission(interaction: discord.Interaction):
    """Assigns or checks mission status."""
    user_id = interaction.user.id
    if user_id not in player_profiles:
        await interaction.response.send_message("Veuillez d'abord créer un profil avec `/profile`.", ephemeral=True)
        return

    player = player_profiles[user_id]
    if player.active_mission_id:
        current_mission = available_missions[player.active_mission_id]
        progress = "Vous avez le colis." if player.mission_progress.get("package_collected") else "Vous devez récupérer le colis."
        await interaction.response.send_message(f"**Mission en cours : {current_mission.name}**\n{current_mission.description}\n*Statut : {progress}*")
        return

    # Assign "Livraison Sombre"
    mission_id = "livraison_sombre"
    player.active_mission_id = mission_id
    player.mission_progress = {"package_collected": False}

    if save_player_data():
        assigned_mission = available_missions[mission_id]
        await interaction.response.send_message(f"**Nouvelle mission acceptée : {assigned_mission.name}**\n{assigned_mission.description}")
    else:
        # Revert state
        player.active_mission_id = None
        player.mission_progress = {}
        await handle_save_error(interaction)

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
    load_player_data()
    load_world_data()
    if TOKEN is None:
        print("Error: DISCORD_TOKEN environment variable not set.")
        print("Please create a .env file and add your token, e.g., DISCORD_TOKEN=your_token_here")
    else:
        bot.run(TOKEN)
