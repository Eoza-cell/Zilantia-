import discord
from discord.ext import commands, tasks
import sqlite3
import requests
import os

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_luxium_distribution.start()

    def cog_unload(self):
        self.daily_luxium_distribution.cancel()

    @commands.hybrid_command(name="image", description="Génère une image via une IA.")
    async def image(self, ctx, *, prompt: str):
        """Génère une image à partir d'un prompt en utilisant Pollinations.ai."""
        await ctx.defer()
        # L'URL de l'API de Pollinations.ai peut changer, à vérifier si cela ne fonctionne plus.
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP

            # Discord ne peut pas envoyer de fichier depuis une URL directement de cette manière.
            # Il faut la joindre dans un embed ou l'envoyer comme un lien.
            embed = discord.Embed(title="Image générée par IA", description=f"**Prompt :** {prompt}", color=discord.Color.blue())
            embed.set_image(url=url)
            embed.set_footer(text="Généré via Pollinations.ai")
            await ctx.send(embed=embed)

        except requests.exceptions.RequestException as e:
            await ctx.send(f"Une erreur est survenue lors de la communication avec l'API d'image. Détails: {e}", ephemeral=True)


    @tasks.loop(hours=24)
    async def daily_luxium_distribution(self):
        """Distributes Luxium to territory owners daily."""
        print("Distributing daily Luxium...")
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        revenue_map = {'Village': 50, 'Ville': 150, 'Cité': 300, 'Royaume': 700, 'Empire': 1500}

        try:
            cursor.execute("SELECT owner_character_id, type FROM territories WHERE owner_character_id IS NOT NULL")
            territories = cursor.fetchall()

            updated_characters = 0
            for owner_char_id, territory_type in territories:
                revenue = revenue_map.get(territory_type, 0)
                if revenue > 0:
                    cursor.execute("UPDATE characters SET luxium = luxium + ? WHERE id = ?", (revenue, owner_char_id))
                    updated_characters += 1

            conn.commit()
            print(f"Luxium distribution complete. {updated_characters} characters received income.")

        except sqlite3.Error as e:
            print(f"Error during Luxium distribution: {e}")

        finally:
            conn.close()

    @daily_luxium_distribution.before_loop
    async def before_daily_distribution(self):
        await self.bot.wait_until_ready()
        print("La tâche de distribution de Luxium est prête.")

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
