import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from .utils.db_helpers import get_active_character, get_territory_by_name_for_character

class NpcCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    npc_group = app_commands.Group(name="npc", description="Gérez les Personnages Non-Joueurs (PNJ).")

    @npc_group.command(name="create", description="Crée un nouveau PNJ dans un de vos territoires.")
    @app_commands.describe(nom="Le nom du PNJ.", role="Son rôle.", nom_territoire="Le nom de votre territoire.", loyaute="Sa loyauté (0-100).", hostilite="Son hostilité (0-100).")
    async def create(self, interaction: discord.Interaction, nom: str, role: str, nom_territoire: str, loyaute: int = 50, hostilite: int = 10):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_territory_by_name_for_character(active_character['id'], nom_territoire)
        if not territory:
            await interaction.response.send_message(f"Vous ne possédez pas de territoire nommé **{nom_territoire}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO pnjs_dynamiques (name, role, loyalty, hostility, territory_id) VALUES (?, ?, ?, ?, ?)", (nom, role, loyaute, hostilite, territory['id']))
            conn.commit()
            await interaction.response.send_message(f"Le PNJ **{nom}** ({role}) a été créé dans **{nom_territoire}**.")
        except sqlite3.Error as e:
            await interaction.response.send_message(f"Erreur lors de la création du PNJ : {e}", ephemeral=True)
        finally:
            conn.close()

    @npc_group.command(name="delete", description="Supprime un PNJ de votre territoire.")
    @app_commands.describe(nom_pnj="Le nom du PNJ.", nom_territoire="Le nom du territoire.")
    async def delete(self, interaction: discord.Interaction, nom_pnj: str, nom_territoire: str):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_territory_by_name_for_character(active_character['id'], nom_territoire)
        if not territory:
            await interaction.response.send_message(f"Vous ne possédez pas de territoire nommé **{nom_territoire}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pnjs_dynamiques WHERE name = ? AND territory_id = ?", (nom_pnj, territory['id']))

        if cursor.rowcount > 0:
            conn.commit()
            await interaction.response.send_message(f"Le PNJ **{nom_pnj}** a été supprimé de **{nom_territoire}**.")
        else:
            await interaction.response.send_message(f"Aucun PNJ nommé **{nom_pnj}** dans **{nom_territoire}**.", ephemeral=True)
        conn.close()

    @npc_group.command(name="list", description="Affiche les PNJ d'un de vos territoires.")
    @app_commands.describe(nom_territoire="Le nom du territoire.")
    async def list(self, interaction: discord.Interaction, nom_territoire: str):
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_territory_by_name_for_character(active_character['id'], nom_territoire)
        if not territory:
            await interaction.response.send_message(f"Vous ne possédez pas de territoire nommé **{nom_territoire}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pnjs_dynamiques WHERE territory_id = ?", (territory['id'],))
        npcs = cursor.fetchall()
        conn.close()

        if not npcs:
            await interaction.response.send_message(f"Il n'y a aucun PNJ dans **{nom_territoire}**.", ephemeral=True)
            return

        embed = discord.Embed(title=f"PNJ de {nom_territoire}", color=discord.Color.blue())
        for npc in npcs:
            embed.add_field(name=f"**{npc['name']}** - {npc['role']}", value=f"Loyauté: {npc['loyalty']}% | Hostilité: {npc['hostility']}%", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(NpcCog(bot))
