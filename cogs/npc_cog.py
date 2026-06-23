import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from .utils.db_helpers import get_npc_by_name, get_npcs, get_db_connection

class NPCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_or_create_webhook(self, channel):
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
            return None

        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="Aetheris Proxy")
        if webhook is None:
            webhook = await channel.create_webhook(name="Aetheris Proxy")
        return webhook

    @app_commands.command(name="npc-dire", description="Faire parler un PNJ via proxy.")
    @app_commands.describe(npc_name="Le nom du PNJ.", message="Ce que le PNJ doit dire.")
    async def npc_say(self, interaction: discord.Interaction, npc_name: str, message: str):
        if interaction.guild is None:
            await interaction.response.send_message("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        npc = get_npc_by_name(npc_name)
        if not npc:
            await interaction.response.send_message(f"Le PNJ **{npc_name}** n'existe pas.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        webhook = await self.get_or_create_webhook(interaction.channel)
        if webhook is None:
            await interaction.followup.send("Impossible de créer un webhook dans ce canal.", ephemeral=True)
            return

        await webhook.send(
            content=message,
            username=npc['name'],
            avatar_url=npc['avatar_url']
        )

        await interaction.followup.send(f"Message envoyé pour {npc_name}.", ephemeral=True)

    @app_commands.command(name="npc-liste", description="Liste tous les PNJ disponibles.")
    async def npc_list(self, interaction: discord.Interaction):
        npcs = get_npcs()
        if not npcs:
            await interaction.response.send_message("Aucun PNJ trouvé.")
            return

        embed = discord.Embed(title="👥 PNJ d'Aetheris", color=discord.Color.light_grey())
        for npc in npcs:
            embed.add_field(name=npc['name'], value=f"Rôle: {npc['role']}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="npc-creer", description="Créer un nouveau PNJ (Admin).")
    @app_commands.describe(nom="Nom du PNJ", role="Rôle du PNJ", avatar_url="URL de l'image de profil")
    async def npc_create(self, interaction: discord.Interaction, nom: str, role: str, avatar_url: str):
        # In a real scenario, check for admin permissions
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO npcs (name, role, avatar_url) VALUES (?, ?, ?)", (nom, role, avatar_url))
            conn.commit()
            await interaction.response.send_message(f"PNJ **{nom}** créé avec succès.")
        except Exception as e:
            await interaction.response.send_message(f"Erreur lors de la création : {e}")
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(NPCCog(bot))
