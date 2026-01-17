import discord
from discord.ext import commands
from discord import app_commands

from cogs.utils.db_helpers import get_db_connection

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="artefact_create", description="Crée un nouvel artefact dans le jeu.")
    @app_commands.checks.has_permissions(administrator=True)
    async def artefact_create(self, interaction: discord.Interaction, name: str, description: str, rarity: str):
        await interaction.response.defer(ephemeral=True)

        rarity_options = ['Commun', 'Rare', 'Légendaire', 'Unique']
        if rarity.capitalize() not in rarity_options:
            await interaction.followup.send(f"Rareté invalide. Veuillez choisir parmi: {', '.join(rarity_options)}.")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO artefacts (name, description, rarity) VALUES (?, ?, ?)",
                           (name, description, rarity.capitalize()))
            conn.commit()
            conn.close()
            await interaction.followup.send(f"L'artefact '{name}' a été créé avec succès.")
        except Exception as e:
            print(f"Error in /artefact_create: {e}")
            await interaction.followup.send("Une erreur est survenue lors de la création de l'artefact.")

    @app_commands.command(name="give_artefact", description="Donne un artefact à un personnage.")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_artefact(self, interaction: discord.Interaction, member: discord.Member, artefact_name: str):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Find the artefact by name
            cursor.execute("SELECT id FROM artefacts WHERE name = ?", (artefact_name,))
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
            ''', (member.id,))
            character = cursor.fetchone()
            if not character:
                await interaction.followup.send(f"L'utilisateur {member.display_name} n'a pas de personnage actif.")
                conn.close()
                return

            # Give the artefact to the character
            cursor.execute("INSERT INTO character_artefacts (character_id, artefact_id) VALUES (?, ?)",
                           (character['id'], artefact['id']))
            conn.commit()
            conn.close()

            await interaction.followup.send(f"L'artefact '{artefact_name}' a été donné à {member.display_name}.")

        except Exception as e:
            print(f"Error in /give_artefact: {e}")
            await interaction.followup.send("Une erreur est survenue lors de l'attribution de l'artefact.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
