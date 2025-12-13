import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# --- Helper Functions for Database Interaction ---

def get_player_by_discord_id(discord_id: int):
    """Fetches a player record from the database using their Discord ID."""
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (discord_id,))
    player = cursor.fetchone()
    conn.close()
    return player

def create_player(discord_id: int, discord_name: str):
    """Creates a new player record in the database."""
    conn = sqlite3.connect('arcanes.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO players (user_id, user_name) VALUES (?, ?)", (discord_id, discord_name))
    conn.commit()
    conn.close()
    return get_player_by_discord_id(discord_id)

def get_active_character(discord_id: int):
    """Fetches the currently active character for a given Discord user."""
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.* FROM characters c
        JOIN players p ON c.player_id = p.id
        WHERE p.user_id = ? AND p.active_character_id = c.id
    """, (discord_id,))
    character = cursor.fetchone()
    conn.close()
    return character

def get_character_by_name(player_id: int, name: str):
    """Fetches a character by name for a specific player."""
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE player_id = ? AND name = ?", (player_id, name))
    character = cursor.fetchone()
    conn.close()
    return character

def get_player_characters(player_id: int):
    """Fetches all characters belonging to a player."""
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE player_id = ?", (player_id,))
    characters = cursor.fetchall()
    conn.close()
    return characters

# --- Character Cog ---

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    character_group = app_commands.Group(name="character", description="Gérez vos personnages dans l'Ère des Arcanes.")

    @character_group.command(name="create", description="Crée un nouveau personnage.")
    async def create(self, interaction: discord.Interaction, nom: str):
        """Creates a new character for the player."""
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        # Check if a character with the same name already exists for this player
        if get_character_by_name(player['id'], nom):
            await interaction.response.send_message(f"Vous avez déjà un personnage nommé **{nom}**. Choisissez un nom différent.", ephemeral=True)
            return

        # Create the character
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO characters (player_id, name) VALUES (?, ?)", (player['id'], nom))
        new_character_id = cursor.lastrowid

        # If this is the player's first character, set it as active
        if not player['active_character_id']:
            cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (new_character_id, player['id']))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Votre personnage **{nom}** a été créé avec succès ! Si c'est votre premier, il est maintenant votre personnage actif.")

    @character_group.command(name="switch", description="Changez de personnage actif.")
    async def switch(self, interaction: discord.Interaction, nom: str):
        """Switches the active character."""
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage. Créez-en un avec `/character create`.", ephemeral=True)
            return

        target_character = get_character_by_name(player['id'], nom)
        if not target_character:
            await interaction.response.send_message(f"Vous n'avez pas de personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (target_character['id'], player['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Votre personnage actif est maintenant **{nom}**.")

    @character_group.command(name="list", description="Affiche la liste de vos personnages.")
    async def list(self, interaction: discord.Interaction):
        """Lists all of the player's characters."""
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        characters = get_player_characters(player['id'])
        if not characters:
            await interaction.response.send_message("Vous n'avez pas encore de personnage. Utilisez `/character create`.", ephemeral=True)
            return

        active_char_id = player['active_character_id']
        description = ""
        for char in characters:
            status = " (Actif)" if char['id'] == active_char_id else ""
            description += f"- **{char['name']}**{status}\n"

        embed = discord.Embed(title=f"Personnages de {interaction.user.name}", description=description, color=discord.Color.dark_green())
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="profile", description="Affiche le profil de votre personnage actif.")
    async def profile(self, interaction: discord.Interaction):
        """Displays the profile of the active character."""
        character = get_active_character(interaction.user.id)

        if not character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif. Créez-en un avec `/character create` ou activez-en un avec `/character switch`.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Profil de {character['name']}", color=discord.Color.dark_purple())
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.add_field(name="Rang", value=character['rang'], inline=True)
        embed.add_field(name="Points de Puissance (PP)", value=character['pp'], inline=True)
        embed.add_field(name="💰 Luxium", value=f"{character['luxium']}", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    cog = CharacterCog(bot)
    bot.tree.add_command(cog.character_group)
    bot.tree.add_command(cog.profile) # Manually add other commands as they are not in the group
    await bot.add_cog(cog)
