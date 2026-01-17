import discord
from discord.ext import commands
from discord import app_commands

from cogs.utils.db_helpers import get_db_connection
from cogs.utils.db_helpers import get_active_character

class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inventory", description="Affiche l'inventaire de votre personnage actif.")
    async def inventory(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        try:
            character = get_active_character(user_id)
            if character is None:
                await interaction.followup.send(
                    "Vous n'avez pas de personnage actif. Veuillez en créer un ou en sélectionner un.",
                    ephemeral=True
                )
                return

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT a.name, a.rarity, a.description
                FROM artefacts a
                JOIN character_artefacts ca ON a.id = ca.artefact_id
                WHERE ca.character_id = ?
            ''', (character['id'],))

            artefacts = cursor.fetchall()
            conn.close()

            embed = discord.Embed(
                title=f"Inventaire de {character['name']}",
                color=discord.Color.gold()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)

            if not artefacts:
                embed.description = "Votre inventaire est vide."
            else:
                for artefact in artefacts:
                    embed.add_field(
                        name=f"{artefact['name']} ({artefact['rarity']})",
                        value=artefact['description'],
                        inline=False
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in /inventory command: {e}")
            await interaction.followup.send("Une erreur est survenue lors de la récupération de votre inventaire.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
