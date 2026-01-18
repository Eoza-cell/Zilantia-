import discord
from discord.ext import commands
from discord import app_commands
import requests

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="image", description="Génère une image via une IA.")
    @app_commands.describe(prompt="La description de l'image à générer.")
    async def image(self, interaction: discord.Interaction, prompt: str):
        """Generates an image from a prompt using Pollinations.ai."""
        await interaction.response.defer()
        # Corrected URL based on user-provided curl command
        url = f"https://gen.pollinations.ai/image/{prompt.replace(' ', '%20')}"

        try:
            # Use a HEAD request to check the content type before sending the embed
            response = requests.head(url, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get('content-type')
            if not content_type or not content_type.startswith('image/'):
                 raise requests.exceptions.RequestException("API did not return a valid image.")

            embed = discord.Embed(title="Image générée par IA", description=f"**Prompt :** {prompt}", color=discord.Color.blue())
            embed.set_image(url=url)
            embed.set_footer(text="Généré via Pollinations.ai")
            await interaction.followup.send(embed=embed)

        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"Une erreur est survenue lors de la génération de l'image. L'API est peut-être indisponible. Erreur : {e}", ephemeral=True)

    @app_commands.command(name="texte", description="Génère un texte via une IA.")
    @app_commands.describe(prompt="Le début du texte à générer.")
    async def text(self, interaction: discord.Interaction, prompt: str):
        """Generates text from a prompt using Pollinations.ai."""
        await interaction.response.defer()
        url = f"https://gen.pollinations.ai/text/{prompt.replace(' ', '%20')}"

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()

            # The API returns a JSON object with the text in the 'text' key
            data = response.json()
            generated_text = data.get("text", "Le texte généré n'a pas pu être extrait de la réponse.")

            embed = discord.Embed(title="Texte généré par IA", description=f"**Prompt :** {prompt}", color=discord.Color.green())
            embed.add_field(name="Résultat", value=generated_text)
            embed.set_footer(text="Généré via Pollinations.ai")
            await interaction.followup.send(embed=embed)

        except requests.exceptions.RequestException as e:
            await interaction.followup.send(f"Une erreur est survenue lors de la génération du texte. Erreur : {e}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Une erreur inattendue est survenue : {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
