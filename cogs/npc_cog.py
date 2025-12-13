import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# --- Helper Functions for Database Interaction ---

def get_territory_by_name(owner_character_id: int, name: str):
    """Fetches a territory by its name for a specific character."""
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM territories WHERE owner_character_id = ? AND name = ?", (owner_character_id, name))
    territory = cursor.fetchone()
    conn.close()
    return territory

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

# --- NPC Cog ---

class NpcCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    npc_group = app_commands.Group(name="npc", description="Gérez les Personnages Non-Joueurs (PNJ).")

    @npc_group.command(name="create", description="Crée un nouveau PNJ dans un de vos territoires.")
    @app_commands.describe(nom="Le nom du PNJ.", role="Son rôle (ex: Marchand, Capitaine de la garde).", nom_territoire="Le nom de votre territoire où il résidera.", loyaute="Sa loyauté initiale (0-100).", hostilite="Son hostilité initiale (0-100).")
    async def create(self, interaction: discord.Interaction, nom: str, role: str, nom_territoire: str, loyaute: int = 50, hostilite: int = 10):
        """Creates a new NPC and assigns it to a territory."""
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_territory_by_name(active_character['id'], nom_territoire)
        if not territory:
            await interaction.response.send_message(f"Vous ne possédez pas de territoire nommé **{nom_territoire}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO pnjs_dynamiques (name, role, loyalty, hostility, territory_id)
                VALUES (?, ?, ?, ?, ?)
            """, (nom, role, loyaute, hostilite, territory['id']))
            conn.commit()
            await interaction.response.send_message(f"Le PNJ **{nom}** ({role}) a été créé et ajouté à votre territoire **{nom_territoire}**.")
        except sqlite3.Error as e:
            await interaction.response.send_message(f"Une erreur est survenue lors de la création du PNJ : {e}", ephemeral=True)
        finally:
            conn.close()

    @npc_group.command(name="list", description="Affiche la liste des PNJ dans un de vos territoires.")
    @app_commands.describe(nom_territoire="Le nom du territoire dont vous voulez voir les PNJ.")
    async def list(self, interaction: discord.Interaction, nom_territoire: str):
        """Lists all NPCs in a specified territory."""
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_territory_by_name(active_character['id'], nom_territoire)
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
            await interaction.response.send_message(f"Il n'y a aucun PNJ dans votre territoire de **{nom_territoire}**.", ephemeral=True)
            return

        embed = discord.Embed(title=f"PNJ de {nom_territoire}", color=discord.Color.blue())
        for npc in npcs:
            embed.add_field(
                name=f"**{npc['name']}** - {npc['role']}",
                value=f"Loyauté: {npc['loyalty']}% | Hostilité: {npc['hostility']}%",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    cog = NpcCog(bot)
    bot.tree.add_command(cog.npc_group)
    await bot.add_cog(cog)
