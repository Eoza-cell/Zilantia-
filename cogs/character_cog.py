import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
from .utils.db_helpers import get_player_by_discord_id, create_player, get_character_by_name_for_player, get_player_characters, get_active_character

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    POWER_TYPES = [
        "Électrokinésie", "Pyrokinésie", "Cryokinésie",
        "Manipulation mentale", "Invisibilité", "Perception altérée", "Corruption"
    ]

    @app_commands.command(name="start", description="Commencez votre éveil dans Aetheris.")
    @app_commands.describe(nom="Le nom de votre personnage.")
    async def start(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        characters = get_player_characters(player['id'])
        if characters:
            await interaction.response.send_message("Vous avez déjà un personnage ! Utilisez `/character list` pour les voir.", ephemeral=True)
            return

        # Initial stats allocation
        stats = {
            "str": random.randint(8, 12),
            "agi": random.randint(8, 12),
            "def": random.randint(8, 12),
            "pow": random.randint(8, 12),
            "acc": random.randint(8, 12),
            "end": random.randint(8, 12)
        }
        power = random.choice(self.POWER_TYPES)

        conn = sqlite3.connect('aetheris.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO characters (player_id, name, power_type, str, agi, def, pow, acc, end, zone_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (player['id'], nom, power, stats['str'], stats['agi'], stats['def'], stats['pow'], stats['acc'], stats['end'], 1))
        new_character_id = cursor.lastrowid

        cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (new_character_id, player['id']))
        conn.commit()
        conn.close()

        embed = discord.Embed(title=f"Éveil de {nom}", description=f"Bienvenue dans Aetheris, {interaction.user.mention}.", color=discord.Color.blue())
        embed.add_field(name="Pouvoir", value=power, inline=False)
        for stat, val in stats.items():
            embed.add_field(name=stat.upper(), value=str(val), inline=True)
        embed.set_footer(text="Utilisez /profile pour voir vos détails.")

        await interaction.response.send_message(embed=embed)

    character_group = app_commands.Group(name="character", description="Gérez vos personnages Aetheris.")

    @character_group.command(name="list", description="Liste vos personnages.")
    async def list_chars(self, interaction: discord.Interaction):
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
            description += f"- **{char['name']}** - {char['power_type']}{status}\n"

        embed = discord.Embed(title=f"Personnages de {interaction.user.name}", description=description, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @character_group.command(name="switch", description="Change de personnage actif.")
    async def switch(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        target_character = get_character_by_name_for_player(player['id'], nom)
        if not target_character:
            await interaction.response.send_message(f"Vous n'avez pas de personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = sqlite3.connect('aetheris.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (target_character['id'], player['id']))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Votre personnage actif est maintenant **{nom}**.")

    @app_commands.command(name="profile", description="Affiche votre profil Aetheris.")
    async def profile(self, interaction: discord.Interaction):
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Aucun personnage actif. Utilisez `/start`.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Profil : {character['name']}", color=discord.Color.dark_red())
        embed.add_field(name="Pouvoir", value=character['power_type'], inline=False)
        embed.add_field(name="Faction", value=character['faction_name'] or "Indépendant", inline=True)
        embed.add_field(name="Zone actuelle", value=character['zone_name'] or "Inconnue", inline=True)
        embed.add_field(name="Niveau", value=f"{character['level']} ({character['xp']} XP)", inline=True)

        stats_text = (
            f"STR: {character['str']} | AGI: {character['agi']} | DEF: {character['def']}\n"
            f"POW: {character['pow']} | ACC: {character['acc']} | END: {character['end']}"
        )
        embed.add_field(name="Statistiques", value=stats_text, inline=False)

        hp_bar = f"{character['hp']}/{character['max_hp']} PV"
        fatigue_bar = f"{character['fatigue']}/100 Fatigue"
        embed.add_field(name="État", value=f"{hp_bar}\n{fatigue_bar}\nStatut: {character['status']}", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
