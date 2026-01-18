import discord
from discord.ext import commands
from discord import app_commands

from cogs.utils.db_helpers import get_db_connection

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="creer_artefact", description="Crée un nouvel artefact.")
    @app_commands.describe(nom="Le nom de l'artefact.", description="La description de l'artefact.", rarete="La rareté de l'artefact (Commun, Rare, Légendaire, Unique).")
    @app_commands.checks.has_permissions(administrator=True)
    async def artefact_create(self, interaction: discord.Interaction, nom: str, description: str, rarete: str):
        await interaction.response.defer(ephemeral=True)

        rarity_options = ['Commun', 'Rare', 'Légendaire', 'Unique']
        if rarete.capitalize() not in rarity_options:
            await interaction.followup.send(f"Rareté invalide. Veuillez choisir parmi: {', '.join(rarity_options)}.")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO artefacts (name, description, rarity) VALUES (?, ?, ?)",
                           (nom, description, rarete.capitalize()))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"L'artefact '{nom}' a été créé avec succès.")
        except Exception as e:
            print(f"Error in /creer_artefact: {e}")
            await interaction.followup.send("Une erreur est survenue lors de la création de l'artefact.")

    @app_commands.command(name="donner_artefact", description="Donne un artefact à un personnage.")
    @app_commands.describe(membre="Le membre à qui donner l'artefact.", nom_artefact="Le nom de l'artefact.")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_artefact(self, interaction: discord.Interaction, membre: discord.Member, nom_artefact: str):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Find the artefact by name
            cursor.execute("SELECT id FROM artefacts WHERE name = ?", (nom_artefact,))
            artefact = cursor.fetchone()
            if not artefact:
                await interaction.followup.send("Cet artefact n'existe pas.")
                conn.close()
                return

            # Find the user's active character
            cursor.execute('''
                SELECT c.id
                FROM characters c
                JOIN players p ON c.player_id = p.id
                WHERE p.user_id = ? AND p.active_character_id = c.id
            ''', (membre.id,))
            character = cursor.fetchone()
            if not character:
                await interaction.followup.send(f"L'utilisateur {membre.display_name} n'a pas de personnage actif.")
                conn.close()
                return

            # Give the artefact to the character
            cursor.execute("INSERT INTO character_artefacts (character_id, artefact_id) VALUES (?, ?)",
                           (character['id'], artefact['id']))
            conn.commit()
            conn.close()

            await interaction.followup.send(f"L'artefact '{nom_artefact}' a été donné à {membre.display_name}.")

        except Exception as e:
            print(f"Error in /donner_artefact: {e}")
            await interaction.followup.send("Une erreur est survenue lors de l'attribution de l'artefact.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
