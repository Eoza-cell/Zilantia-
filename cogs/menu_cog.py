import discord
from discord.ext import commands
from discord import app_commands, ui
from .utils.db_helpers import get_active_character, get_character_territory

class MenuView(ui.View):
    def __init__(self, territory_data, character_data):
        super().__init__(timeout=180)
        self.territory_data = territory_data
        self.character_data = character_data

    async def generate_embed(self):
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
        embed.set_footer(text="Les boutons d'action seront bientôt disponibles.")
        return embed

    @ui.button(label="Fermer le Menu", style=discord.ButtonStyle.danger, emoji="❌")
    async def close_menu(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.message.delete()
        await interaction.response.send_message("Menu fermé.", ephemeral=True)

class MenuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="menu", description="Ouvre le menu de gestion de territoire.")
    async def menu(self, interaction: discord.Interaction):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif. Utilisez `/start` pour créer votre premier personnage.", ephemeral=True)
            return

        territory = get_character_territory(active_character['id'])
        if not territory:
            await interaction.response.send_message("Votre personnage ne possède pas de territoire.", ephemeral=True)
            return

        view = MenuView(territory, active_character)
        embed = await view.generate_embed()

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(MenuCog(bot))
