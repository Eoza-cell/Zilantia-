import discord
from discord.ext import commands
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
intents.message_content = True  # Required to read message content
intents.members = True # Required to access member information

bot = commands.Bot(intents=intents)

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

class Player:
    def __init__(self, user_id, user_name, user_avatar_url, race, pouvoir):
        self.user_id = user_id
        self.user_name = user_name
        self.user_avatar_url = user_avatar_url
        self.race = race
        self.pouvoir = pouvoir
        self.niveau = 1
        self.health = 100 # Players start with 100 health
        self.traits_uniques = "Aucun pour le moment."
        self.artefact = "Aucun pour le moment."
        self.location_key = None # Player starts nowhere

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
            "location_key": self.location_key
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
        player.health = data.get("health", 100) # Default to 100 for older profiles
        player.traits_uniques = data["traits_uniques"]
        player.artefact = data["artefact"]
        player.location_key = data["location_key"]
        return player

# --- Player Data ---
PLAYER_DATA_FILE = "player_data.json"
player_profiles = {}

def save_player_data():
    """Saves the player profiles to a JSON file."""
    data_to_save = {user_id: player.to_dict() for user_id, player in player_profiles.items()}
    with open(PLAYER_DATA_FILE, 'w') as f:
        json.dump(data_to_save, f, indent=4)

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
    """Saves the world state to a JSON file."""
    data_to_save = {key: loc.to_dict() for key, loc in world_locations.items()}
    with open(WORLD_DATA_FILE, 'w') as f:
        json.dump(data_to_save, f, indent=4)

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
                    pnjs=[PNJ(**pnj_data) for pnj_data in loc_data["pnjs"]],
                    items=[Item(**item_data) for item_data in loc_data["items"]],
                    exits=loc_data["exits"],
                    enemies=[Enemy(**enemy_data) for enemy_data in loc_data["enemies"]]
                )
    except FileNotFoundError:
        # If the file doesn't exist, create and save a default world state
        print("World data file not found, creating a new one.")
        world_locations = {
            "entrepot": Location(
                name="Entrepôt 7",
                description="Un vieil entrepôt sur les quais. L'air est lourd d'humidité et de l'odeur du poisson.",
                pnjs=[PNJ("Marco", "Un docker balafré au regard suspicieux.", "Qu'est-ce que tu veux, étranger ?")],
                items=[Item("Caisse en bois", "Une caisse lourde et fermée. Impossible de voir ce qu'il y a à l'intérieur.")],
                exits={"sud": "ruelle"}
            ),
            "bar": Location(
                name="Le Néon Noir",
                description="Un bar clandestin faiblement éclairé, où la fumée de cigarette danse dans la lumière des néons.",
                pnjs=[PNJ("Lila", "Une barmaid au sourire énigmatique.", "Sers-toi un verre. Ou cause-moi, si t'as le cran.")],
                exits={"est": "ruelle"}
            ),
            "ruelle": Location(
                name="La Ruelle des Murmures",
                description="Une ruelle étroite et sombre, les murs couverts de graffitis mystérieux.",
                items=[Item("Vieux journal", "Un journal datant de plusieurs semaines. Un article sur une disparition a été encerclé.")],
                exits={"nord": "entrepot", "ouest": "bar"},
                enemies=[Enemy("Voyou des Rues", 30, 5)]
            )
        }
        save_world_data()

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
    save_player_data()

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

@bot.tree.command(name="profile", description="Crée ou met à jour la fiche de votre personnage.")
async def profile(interaction: discord.Interaction, race: str, pouvoir: str):
    """Creates or updates a player's character profile."""
    user_id = interaction.user.id

    # Create a new Player object
    player = Player(
        user_id=interaction.user.id,
        user_name=interaction.user.name,
        user_avatar_url=str(interaction.user.avatar.url),
        race=race,
        pouvoir=pouvoir
    )
    player_profiles[user_id] = player
    save_player_data()

    # Create the embed for the profile sheet
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

    await interaction.response.send_message(embed=embed)

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
        player.location_key = new_location_key
        save_player_data()
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

@bot.tree.command(name="fight", description="Active le mode combat.")
async def fight(interaction: discord.Interaction):
    """Activates combat mode."""
    user_id = interaction.user.id
    if user_id not in player_profiles or player_profiles[user_id].location_key is None:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.")
        return

    player = player_profiles[user_id]
    location = world_locations[player.location_key]

    if not location.enemies:
        await interaction.response.send_message("Il n'y a personne à combattre ici.")
        return

    # For simplicity, we'll fight the first enemy in the list
    enemy = location.enemies[0]
    player_damage = random.randint(10, 20) # Player damage is random for now

    # Simple combat loop
    combat_log = ""
    while player.health > 0 and enemy.health > 0:
        # Player attacks
        enemy.health -= player_damage
        combat_log += f"Vous attaquez {enemy.name} et lui infligez {player_damage} points de dégâts.\n"
        if enemy.health <= 0:
            combat_log += f"Vous avez vaincu {enemy.name} !\n"
            location.enemies.pop(0) # Remove the defeated enemy
            save_world_data() # Save the world state
            save_player_data()
            break

        # Enemy attacks
        player.health -= enemy.damage
        combat_log += f"{enemy.name} vous attaque et vous inflige {enemy.damage} points de dégâts.\n"
        if player.health <= 0:
            combat_log += "Vous avez été vaincu...\n"
            # Reset player health for next time
            player.health = 100
            save_player_data()
            break

    await interaction.response.send_message(f"**--- RAPPORT DE COMBAT ---**\n{combat_log}")

@bot.tree.command(name="interact", description="Interagir avec un PNJ ou un objet.")
async def interact(interaction: discord.Interaction, target: str):
    """Interacts with a target."""
    user_id = interaction.user.id
    if user_id not in player_profiles or player_profiles[user_id].location_key is None:
        await interaction.response.send_message("Vous n'êtes nulle part. Utilisez `/start` pour commencer votre aventure.")
        return

    player = player_profiles[user_id]
    location = world_locations[player.location_key]
    target_lower = target.lower()

    # Check for PNJs
    for pnj in location.pnjs:
        if pnj.name.lower() == target_lower:
            await interaction.response.send_message(f"**{pnj.name}**: \"{pnj.dialogue}\"")
            return

    # Check for items
    for item in location.items:
        if item.name.lower() == target_lower:
            await interaction.response.send_message(f"Vous examinez **{item.name}**: {item.description}")
            return

    await interaction.response.send_message(f"Impossible de trouver '{target}' ici.")

@bot.tree.command(name="portal", description="Tente d'ouvrir une brèche dimensionnelle.")
async def portal(interaction: discord.Interaction):
    """Attempts to open a portal."""
    await interaction.response.send_message("Vous essayez d'ouvrir un portail, mais rien ne se passe. Peut-être que le pouvoir vous manque...")

@bot.tree.command(name="mission", description="Génère une mission dynamique.")
async def mission(interaction: discord.Interaction):
    """Generates a dynamic mission."""
    missions = [
        "**Livraison Sombre**: Un paquet suspect doit être livré à l'autre bout de la ville. Discrétion requise.",
        "**Nettoyage de Rue**: Un gang rival empiète sur votre territoire. Il est temps de leur envoyer un message.",
        "**Crash sur le Port**: Une cargaison illégale vient d'arriver. Récupérez-la avant la police.",
    ]
    await interaction.response.send_message(f"Nouvelle mission disponible : {random.choice(missions)}")

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
