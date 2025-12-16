import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from .utils.db_helpers import get_player_by_discord_id, create_player, get_character_by_name_for_player, get_player_characters

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start", description="Commencez l'aventure et créez votre premier personnage.")
    @app_commands.describe(nom="Le nom de votre premier personnage.")
    async def start(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        characters = get_player_characters(player['id'])
        if characters:
            await interaction.response.send_message("Vous avez déjà commencé votre aventure ! Utilisez `/character create` pour créer d'autres personnages.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO characters (player_id, name) VALUES (?, ?)", (player['id'], nom))
        new_character_id = cursor.lastrowid

        cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (new_character_id, player['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Bienvenue dans l'Ère des Arcanes ! Votre premier personnage, **{nom}**, a été créé et est maintenant actif. Utilisez `/profile` pour le voir.")

    character_group = app_commands.Group(name="character", description="Gérez vos personnages secondaires.")

    @character_group.command(name="create", description="Crée un nouveau personnage.")
    async def create(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        if get_character_by_name_for_player(player['id'], nom):
            await interaction.response.send_message(f"Vous avez déjà un personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO characters (player_id, name) VALUES (?, ?)", (player['id'], nom))
        new_character_id = cursor.lastrowid

        if not player['active_character_id']:
            cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (new_character_id, player['id']))

        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Votre personnage **{nom}** a été créé.")

    @character_group.command(name="switch", description="Changez de personnage actif.")
    async def switch(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        target_character = get_character_by_name_for_player(player['id'], nom)
        if not target_character:
            await interaction.response.send_message(f"Vous n'avez pas de personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (target_character['id'], player['id']))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Votre personnage actif est maintenant **{nom}**.")

    @character_group.command(name="delete", description="Supprime l'un de vos personnages.")
    @app_commands.describe(nom="Le nom exact du personnage à supprimer.")
    async def delete(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez aucun personnage à supprimer.", ephemeral=True)
            return

        character_to_delete = get_character_by_name_for_player(player['id'], nom)
        if not character_to_delete:
            await interaction.response.send_message(f"Vous n'avez pas de personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM territories WHERE owner_character_id = ?", (character_to_delete['id'],))
        if cursor.fetchone():
            await interaction.response.send_message(f"**{nom}** possède un territoire et ne peut être supprimé.", ephemeral=True)
            conn.close()
            return

        if player['active_character_id'] == character_to_delete['id']:
            cursor.execute("UPDATE players SET active_character_id = NULL WHERE id = ?", (player['id'],))
        cursor.execute("DELETE FROM characters WHERE id = ?", (character_to_delete['id'],))
        cursor.execute("UPDATE artefacts SET owner_character_id = NULL WHERE owner_character_id = ?", (character_to_delete['id'],))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Le personnage **{nom}** a été supprimé.")

    @character_group.command(name="list", description="Affiche la liste de vos personnages.")
    async def list(self, interaction: discord.Interaction):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        characters = get_player_characters(player['id'])
        if not characters:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
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
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif. Utilisez `/start` pour en créer un.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Profil de {character['name']}", color=discord.Color.dark_purple())
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.add_field(name="Rang", value=character['rang'], inline=True)
        embed.add_field(name="Points de Puissance (PP)", value=character['pp'], inline=True)
        embed.add_field(name="💰 Luxium", value=f"{character['luxium']}", inline=True)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
