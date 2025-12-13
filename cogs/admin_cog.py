import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from .utils.db_helpers import get_character_by_name_global

# --- Helper to calculate rank from PP ---
def get_rank_from_pp(pp: int) -> str:
    if pp >= 120: return 'SS'
    if pp >= 95: return 'S'
    if pp >= 80: return 'A'
    if pp >= 60: return 'B'
    if pp >= 40: return 'C'
    if pp >= 25: return 'D'
    if pp >= 10: return 'E'
    return 'F'

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin_group = app_commands.Group(name="admin", description="Commandes administratives pour gérer le jeu.", default_permissions=discord.Permissions(administrator=True))

    @admin_group.command(name="add_pp", description="Ajoute ou retire des Points de Puissance à un personnage.")
    @app_commands.describe(nom_personnage="Le nom exact du personnage à modifier.", quantite="Le nombre de PP à ajouter (peut être négatif).")
    async def add_pp(self, interaction: discord.Interaction, nom_personnage: str, quantite: int):
        target_character = get_character_by_name_global(nom_personnage)
        if not target_character:
            await interaction.response.send_message(f"Aucun personnage nommé **{nom_personnage}** n'a été trouvé.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        new_pp = target_character['pp'] + quantite
        new_rank = get_rank_from_pp(new_pp)

        if new_rank == 'SS' and target_character['rang'] != 'SS':
            cursor.execute("SELECT id FROM world_events WHERE type = 'SS' AND is_active = TRUE")
            ss_event_active = cursor.fetchone()
            if not ss_event_active:
                await interaction.response.send_message("Action bloquée : Promotion au rang SS non autorisée sans événement 'SS' actif.", ephemeral=True)
                conn.close()
                return

            fondateur_role = discord.utils.get(interaction.user.roles, name="Fondateur")
            if not fondateur_role:
                await interaction.response.send_message("Action bloquée : Vous devez avoir le rôle 'Fondateur' pour attribuer le rang SS.", ephemeral=True)
                conn.close()
                return

        cursor.execute("UPDATE characters SET pp = ?, rank = ? WHERE id = ?", (new_pp, new_rank, target_character['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"**{quantite} PP** ajoutés à **{nom_personnage}**. Total : {new_pp} PP. Rang : {new_rank}.")

    @admin_group.command(name="add_luxium", description="Ajoute ou retire du Luxium à un personnage.")
    @app_commands.describe(nom_personnage="Le nom exact du personnage.", quantite="La quantité de Luxium à ajouter (peut être négative).")
    async def add_luxium(self, interaction: discord.Interaction, nom_personnage: str, quantite: int):
        target_character = get_character_by_name_global(nom_personnage)
        if not target_character:
            await interaction.response.send_message(f"Aucun personnage nommé **{nom_personnage}** n'a été trouvé.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        new_balance = target_character['luxium'] + quantite

        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_balance, target_character['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"**{quantite} Luxium** ajoutés à **{nom_personnage}**. Solde : {new_balance} Luxium.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
