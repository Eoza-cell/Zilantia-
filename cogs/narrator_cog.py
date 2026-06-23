import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
from .utils.db_helpers import get_active_character, add_character_memory

class NarratorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("POLLINATION_API_KEY")

    @app_commands.command(name="rp", description="Effectuez une action de Roleplay.")
    @app_commands.describe(action="Décrivez votre action.")
    async def rp_action(self, interaction: discord.Interaction, action: str):
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif. Utilisez `/start`.", ephemeral=True)
            return

        await interaction.response.defer()

        # Build prompt for AI Narrator
        prompt = f"""
        Tu es l'IA narratrice du monde AETHERIS (Urban Supernatural RP).
        Personnage : {character['name']}
        Pouvoir : {character['power_type']}
        Stats : STR:{character['str']}, AGI:{character['agi']}, DEF:{character['def']}, POW:{character['pow']}, ACC:{character['acc']}, END:{character['end']}
        Zone : {character['zone_name']}
        Action du joueur : "{action}"

        Analyse l'action, traduis-la en logique physique basée sur les stats.
        Raconte les conséquences de manière cinématographique, sombre et réaliste.
        Si un PNJ est présent ou mentionné, inclus son dialogue ou sa réaction.
        Respecte la physique et les stats. Ne force pas la victoire.
        Réponds en Français.
        """

        try:
            # Using Pollinations Text API with aiohttp
            api_url = f"https://gen.pollinations.ai/text/{aiohttp.helpers.quote(prompt)}"
            if self.api_key:
                api_url += f"?apikey={self.api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=30) as response:
                    narration = await response.text()

            # Log to character memory
            add_character_memory(character['id'], action, narration)

            embed = discord.Embed(title="Narration Aetheris", description=narration, color=discord.Color.dark_gray())
            embed.set_footer(text=f"Action de {character['name']}")

            # Optional: Generate an image for the scene
            image_url = f"https://image.pollinations.ai/prompt/{aiohttp.helpers.quote('cinematic realistic dark urban supernatural ' + action)}?width=1024&height=512&nologo=true"
            if self.api_key:
                image_url += f"&apikey={self.api_key}"
            embed.set_image(url=image_url)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"L'IA narratrice est momentanément indisponible. ({e})")

async def setup(bot):
    await bot.add_cog(NarratorCog(bot))
