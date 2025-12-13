import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

# --- Helper functions from character_cog ---
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

# --- Territory Cog ---

class TerritoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    territory_group = app_commands.Group(name="territoire", description="Gérez vos territoires.")

    @territory_group.command(name="fonder", description="Fondez votre propre territoire.")
    async def fonder(self, interaction: discord.Interaction, nom_territoire: str):
        """Creates a new territory for the active character."""
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif. Créez-en un ou activez-en un.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        # Check if the character already owns a territory
        cursor.execute("SELECT * FROM territories WHERE owner_character_id = ?", (active_character['id'],))
        if cursor.fetchone():
            await interaction.response.send_message(f"Votre personnage **{active_character['name']}** possède déjà un territoire.", ephemeral=True)
            conn.close()
            return

        # Check cost and balance
        cost = 1000
        if active_character['luxium'] < cost:
            await interaction.response.send_message(f"Il faut {cost} Luxium pour fonder un territoire. Votre personnage n'a pas assez.", ephemeral=True)
            conn.close()
            return

        # Deduct cost and create territory
        new_balance = active_character['luxium'] - cost
        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_balance, active_character['id']))

        cursor.execute("""
            INSERT INTO territories (name, owner_character_id, type)
            VALUES (?, ?, ?)
        """, (nom_territoire, active_character['id'], 'Village'))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Félicitations ! Votre personnage **{active_character['name']}** a fondé le territoire de **{nom_territoire}** pour {cost} Luxium.")

    @territory_group.command(name="view", description="Affiche les informations de votre territoire.")
    async def view(self, interaction: discord.Interaction):
        """Displays details of the active character's territory."""
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM territories WHERE owner_character_id = ?", (active_character['id'],))
        territory = cursor.fetchone()

        if territory:
            embed = discord.Embed(
                title=f"Territoire de {territory['name']}",
                description=f"Dirigé par **{active_character['name']}**",
                color=discord.Color.gold()
            )
            embed.add_field(name="Type", value=territory['type'], inline=True)
            embed.add_field(name="Population", value=territory['population'], inline=True)
            embed.add_field(name="Loyauté", value=f"{territory['loyalty']}%", inline=True)
            embed.add_field(name="Niveau d'Armée", value=territory['army_level'], inline=True)
            embed.add_field(name="Trésorerie", value=f"{territory['luxium_balance']} Luxium", inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"Votre personnage **{active_character['name']}** ne possède pas de territoire.", ephemeral=True)

        conn.close()

async def setup(bot):
    cog = TerritoryCog(bot)
    bot.tree.add_command(cog.territory_group)
    await bot.add_cog(cog)
