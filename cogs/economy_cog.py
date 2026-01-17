import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
from .utils.db_helpers import get_db_connection, get_active_character, get_character_by_name_global

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_luxium_distribution.start()

    def cog_unload(self):
        self.daily_luxium_distribution.cancel()

    @tasks.loop(hours=24)
    async def daily_luxium_distribution(self):
        """Distributes Luxium to territory owners daily."""
        print("Distributing daily Luxium...")
        conn = get_db_connection()
        cursor = conn.cursor()

        revenue_map = {'Village': 10, 'Ville': 50, 'Cité': 150, 'Royaume': 500, 'Empire': 2000}

        try:
            cursor.execute("SELECT owner_character_id, type FROM territories WHERE owner_character_id IS NOT NULL")
            territories = cursor.fetchall()

            updated_characters = 0
            for territory in territories:
                revenue = revenue_map.get(territory['type'], 0)
                if revenue > 0:
                    cursor.execute("UPDATE characters SET luxium = luxium + ? WHERE id = ?", (revenue, territory['owner_character_id']))
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

    @app_commands.command(name="give", description="Donne du Luxium à un autre personnage.")
    @app_commands.describe(destinataire="Le nom du personnage à qui donner du Luxium.", montant="Le montant de Luxium à donner.")
    async def give_luxium(self, interaction: discord.Interaction, destinataire: str, montant: int):
        """Transfers Luxium from the active character to another character."""
        if montant <= 0:
            await interaction.response.send_message("Vous devez donner un montant positif de Luxium.", ephemeral=True)
            return

        sender_char = get_active_character(interaction.user.id)

        if not sender_char:
            await interaction.response.send_message("Vous n'avez pas de personnage actif pour effectuer cette transaction.", ephemeral=True)
            return

        if sender_char['luxium'] < montant:
            await interaction.response.send_message(f"Votre personnage **{sender_char['name']}** n'a pas assez de Luxium. Solde actuel : {sender_char['luxium']}.", ephemeral=True)
            return

        receiver_char = get_character_by_name_global(destinataire)

        if not receiver_char:
            await interaction.response.send_message(f"Aucun personnage nommé **{destinataire}** n'a été trouvé.", ephemeral=True)
            return

        if receiver_char['id'] == sender_char['id']:
            await interaction.response.send_message("Vous ne pouvez pas vous donner de Luxium à vous-même.", ephemeral=True)
            return

        # Perform transaction
        conn = get_db_connection()
        cursor = conn.cursor()

        new_sender_balance = sender_char['luxium'] - montant
        new_receiver_balance = receiver_char['luxium'] + montant

        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_sender_balance, sender_char['id']))
        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_receiver_balance, receiver_char['id']))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"**{sender_char['name']}** a donné **{montant} Luxium** à **{receiver_char['name']}**.")


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
