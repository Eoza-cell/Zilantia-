import discord
from discord.ext import commands
from discord import app_commands
from .utils.db_helpers import get_factions, get_zones, get_active_character, get_db_connection

class WorldCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="villes", description="Liste les zones majeures d'Aetheris.")
    async def list_zones(self, interaction: discord.Interaction):
        zones = get_zones()
        embed = discord.Embed(title="🌆 Zones d'Aetheris", color=discord.Color.dark_blue())

        for zone in zones:
            embed.add_field(
                name=f"{zone['name']} ({zone['type']})",
                value=f"{zone['description']}\nNiveau de danger: {zone['danger_level']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="factions", description="Liste les factions d'Aetheris.")
    async def list_factions(self, interaction: discord.Interaction):
        factions = get_factions()
        embed = discord.Embed(title="⚔️ Factions d'Aetheris", color=discord.Color.red())

        for faction in factions:
            embed.add_field(
                name=faction['name'],
                value=faction['description'],
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="deplacer", description="Se déplacer vers une autre zone.")
    @app_commands.describe(destination="Le nom de la zone de destination.")
    async def move(self, interaction: discord.Interaction, destination: str):
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Aucun personnage actif.", ephemeral=True)
            return

        conn = get_db_connection()
        target_zone = conn.execute("SELECT * FROM zones WHERE name = ?", (destination,)).fetchone()

        if not target_zone:
            await interaction.response.send_message(f"La zone **{destination}** n'existe pas.", ephemeral=True)
            conn.close()
            return

        if character['zone_id'] == target_zone['id']:
            await interaction.response.send_message(f"Vous êtes déjà à **{destination}**.", ephemeral=True)
            conn.close()
            return

        conn.execute("UPDATE characters SET zone_id = ? WHERE id = ?", (target_zone['id'], character['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Vous vous déplacez vers **{destination}**.")

async def setup(bot):
    await bot.add_cog(WorldCog(bot))
