import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="image", description="Génère une image via une IA.")
    @app_commands.describe(prompt="La description de l'image à générer.")
    async def image(self, interaction: discord.Interaction, prompt: str):
        """Generates an image from a prompt using Pollinations.ai."""
        await interaction.response.defer()
        url = f"https://image.pollinations.ai/prompt/{aiohttp.helpers.quote(prompt)}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=10) as response:
                    response.raise_for_status()
                    content_type = response.headers.get('content-type')
                    if not content_type or not content_type.startswith('image/'):
                         raise Exception("Le lien ne pointe pas vers une image valide.")

            embed = discord.Embed(title="Image générée par IA", description=f"**Prompt :** {prompt}", color=discord.Color.blue())
            embed.set_image(url=url)
            embed.set_footer(text="Généré via Pollinations.ai")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Une erreur est survenue lors de la génération de l'image. L'API est peut-être indisponible ou le prompt a été refusé. Erreur : {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
