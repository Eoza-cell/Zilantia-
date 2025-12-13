import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# --- Helper to get a character by name, regardless of owner ---
def get_character_by_name_global(character_name: str):
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE name = ?", (character_name,))
    character = cursor.fetchone()
    conn.close()
    return character

# --- Helper to calculate rank from PP ---
def get_rank_from_pp(pp: int) -> str:
    if pp < 10: return 'F'
    elif pp < 25: return 'E'
    elif pp < 40: return 'D'
    elif pp < 60: return 'C'
    elif pp < 80: return 'B'
    elif pp < 95: return 'A'
    else: return 'S' # Simplified for now

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin_group = app_commands.Group(name="admin", description="Commandes administratives pour gérer le jeu.", default_permissions=discord.Permissions(administrator=True))

    @admin_group.command(name="add_pp", description="Ajoute ou retire des Points de Puissance à un personnage.")
    @app_commands.describe(nom_personnage="Le nom exact du personnage à modifier.", quantite="Le nombre de PP à ajouter (peut être négatif).")
    async def add_pp(self, interaction: discord.Interaction, nom_personnage: str, quantite: int):
        """Adds or removes PP from a specified character."""
        target_character = get_character_by_name_global(nom_personnage)
        if not target_character:
            await interaction.response.send_message(f"Aucun personnage nommé **{nom_personnage}** n'a été trouvé.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        new_pp = target_character['pp'] + quantite
        new_rank = get_rank_from_pp(new_pp)

        cursor.execute("UPDATE characters SET pp = ?, rank = ? WHERE id = ?", (new_pp, new_rank, target_character['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"**{quantite} PP** ont été ajoutés à **{nom_personnage}**. Nouveau total : {new_pp} PP. Nouveau rang : {new_rank}.")

    @admin_group.command(name="add_luxium", description="Ajoute ou retire du Luxium à un personnage.")
    @app_commands.describe(nom_personnage="Le nom exact du personnage.", quantite="La quantité de Luxium à ajouter (peut être négative).")
    async def add_luxium(self, interaction: discord.Interaction, nom_personnage: str, quantite: int):
        """Adds or removes Luxium from a specified character."""
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

        await interaction.response.send_message(f"**{quantite} Luxium** ont été ajoutés à **{nom_personnage}**. Nouveau solde : {new_balance} Luxium.")

async def setup(bot):
    cog = AdminCog(bot)
    # The group is automatically added to the command tree because of the decorator permissions
    await bot.add_cog(cog)
