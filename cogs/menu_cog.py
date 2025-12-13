import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3

# --- Database Helper Functions ---
def get_active_character(discord_id: int):
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT c.* FROM characters c JOIN players p ON c.player_id = p.id WHERE p.user_id = ? AND p.active_character_id = c.id", (discord_id,))
    character = cursor.fetchone()
    conn.close()
    return character

def get_character_territory(character_id: int):
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM territories WHERE owner_character_id = ?", (character_id,))
    territory = cursor.fetchone()
    conn.close()
    return territory

# --- Interactive Territory View ---
class TerritoryMenuView(ui.View):
    def __init__(self, territory_data, character_data):
        super().__init__(timeout=180)
        self.territory_data = territory_data
        self.character_data = character_data

    async def generate_embed(self):
        """Generates the main embed for the territory menu."""
        embed = discord.Embed(
            title=f"Gestion du Territoire : {self.territory_data['name']}",
            description=f"Dirigé par **{self.character_data['name']}**",
            color=discord.Color.dark_green()
        )
        embed.add_field(name="🏰 Type", value=self.territory_data['type'], inline=True)
        embed.add_field(name="👥 Population", value=self.territory_data['population'], inline=True)
        embed.add_field(name="❤️ Loyauté", value=f"{self.territory_data['loyalty']}%", inline=True)
        embed.add_field(name="⚔️ Niveau d'Armée", value=self.territory_data['army_level'], inline=True)
        embed.add_field(name="💰 Trésorerie", value=f"{self.territory_data['luxium_balance']} Luxium", inline=True)
        return embed

    @ui.button(label="Gérer l'Armée", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def manage_army(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Menu de l'armée à implémenter. Utilisez `/armee renforcer` en attendant.", ephemeral=True)

    @ui.button(label="Voir les PNJ", style=discord.ButtonStyle.secondary, emoji="👥")
    async def view_npcs(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Menu des PNJ à implémenter. Utilisez `/npc list` en attendant.", ephemeral=True)

    @ui.button(label="Actions Économiques", style=discord.ButtonStyle.success, emoji="💰")
    async def manage_economy(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Menu de l'économie à implémenter.", ephemeral=True)

    @ui.button(label="Fermer le Menu", style=discord.ButtonStyle.danger, emoji="❌")
    async def close_menu(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("Menu fermé.", ephemeral=True)

# --- Menu Cog ---
class MenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="menu", description="Ouvre le menu de gestion principal.")
    async def menu(self, interaction: discord.Interaction):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_character_territory(active_character['id'])
        if not territory:
            await interaction.response.send_message("Votre personnage ne possède pas de territoire.", ephemeral=True)
            return

        view = TerritoryMenuView(territory, active_character)
        embed = await view.generate_embed()

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(MenuCog(bot))
