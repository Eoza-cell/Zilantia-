import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime
from .utils.db_helpers import get_active_character, get_character_territory

class TerritoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    territory_group = app_commands.Group(name="territoire", description="Gérez vos territoires.")

    @territory_group.command(name="fonder", description="Fondez votre propre territoire.")
    async def fonder(self, interaction: discord.Interaction, nom_territoire: str):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM territories WHERE owner_character_id = ?", (active_character['id'],))
        if cursor.fetchone():
            await interaction.response.send_message(f"Votre personnage **{active_character['name']}** possède déjà un territoire.", ephemeral=True)
            conn.close()
            return

        cost = 1000
        if active_character['luxium'] < cost:
            await interaction.response.send_message(f"Il faut {cost} Luxium pour fonder un territoire.", ephemeral=True)
            conn.close()
            return

        new_balance = active_character['luxium'] - cost
        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_balance, active_character['id']))

        cursor.execute("INSERT INTO territories (name, owner_character_id, type) VALUES (?, ?, ?)", (nom_territoire, active_character['id'], 'Village'))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Félicitations ! **{active_character['name']}** a fondé le territoire de **{nom_territoire}**.")

    @territory_group.command(name="view", description="Affiche les informations de votre territoire.")
    async def view(self, interaction: discord.Interaction):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_character_territory(active_character['id'])

        if territory:
            embed = discord.Embed(title=f"Territoire de {territory['name']}", description=f"Dirigé par **{active_character['name']}**", color=discord.Color.gold())
            embed.add_field(name="Type", value=territory['type'], inline=True)
            embed.add_field(name="Population", value=territory['population'], inline=True)
            embed.add_field(name="Loyauté", value=f"{territory['loyalty']}%", inline=True)
            embed.add_field(name="Niveau d'Armée", value=territory['army_level'], inline=True)
            embed.add_field(name="Trésorerie", value=f"{territory['luxium_balance']} Luxium", inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"**{active_character['name']}** ne possède pas de territoire.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TerritoryCog(bot))
