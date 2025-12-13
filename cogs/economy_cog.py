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

    @tasks.loop(hours=24)
    async def daily_luxium_distribution(self):
        """Distributes Luxium to territory owners daily."""
        print("Distributing daily Luxium...")
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        revenue_map = {'Village': 10, 'Ville': 50, 'Cité': 150, 'Royaume': 500, 'Empire': 2000}

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

    @commands.hybrid_command(name="give", description="Donne du Luxium à un autre personnage.")
    @app_commands.describe(destinataire="Le nom du personnage à qui donner du Luxium.", montant="Le montant de Luxium à donner.")
    async def give_luxium(self, ctx, destinataire: str, montant: int):
        """Transfers Luxium from the active character to another character."""
        if montant <= 0:
            await ctx.send("Vous devez donner un montant positif de Luxium.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get sender's active character
        cursor.execute("SELECT c.* FROM characters c JOIN players p ON c.player_id = p.id WHERE p.user_id = ? AND p.active_character_id = c.id", (ctx.author.id,))
        sender_char = cursor.fetchone()

        if not sender_char:
            await ctx.send("Vous n'avez pas de personnage actif pour effectuer cette transaction.", ephemeral=True)
            conn.close()
            return

        if sender_char['luxium'] < montant:
            await ctx.send(f"Votre personnage **{sender_char['name']}** n'a pas assez de Luxium. Solde actuel : {sender_char['luxium']}.", ephemeral=True)
            conn.close()
            return

        # Get receiver character
        cursor.execute("SELECT * FROM characters WHERE name = ?", (destinataire,))
        receiver_char = cursor.fetchone()

        if not receiver_char:
            await ctx.send(f"Aucun personnage nommé **{destinataire}** n'a été trouvé.", ephemeral=True)
            conn.close()
            return

        if receiver_char['id'] == sender_char['id']:
            await ctx.send("Vous ne pouvez pas vous donner de Luxium à vous-même.", ephemeral=True)
            conn.close()
            return

        # Perform transaction
        new_sender_balance = sender_char['luxium'] - montant
        new_receiver_balance = receiver_char['luxium'] + montant

        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_sender_balance, sender_char['id']))
        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_receiver_balance, receiver_char['id']))

        conn.commit()
        conn.close()

        await ctx.send(f"**{sender_char['name']}** a donné **{montant} Luxium** à **{receiver_char['name']}**.")


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
