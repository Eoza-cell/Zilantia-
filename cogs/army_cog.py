import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

# --- Helper Functions ---

def get_active_character(discord_id: int):
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

def get_character_territory(character_id: int):
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM territories WHERE owner_character_id = ?", (character_id,))
    territory = cursor.fetchone()
    conn.close()
    return territory

def get_territory_by_name_global(name: str):
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM territories WHERE name = ?", (name,))
    territory = cursor.fetchone()
    conn.close()
    return territory

# --- Army Cog ---

class ArmyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    army_group = app_commands.Group(name="armee", description="Gérez votre armée et partez à la conquête.")

    @army_group.command(name="voir", description="Affiche les informations sur l'armée de votre territoire.")
    async def view(self, interaction: discord.Interaction):
        """Displays information about the army of the character's territory."""
        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_character_territory(active_character['id'])
        if not territory:
            await interaction.response.send_message("Votre personnage ne possède pas de territoire.", ephemeral=True)
            return

        # Calculate army power (example formula)
        power = (territory['army_level'] * 50) + (territory['population'] // 10) * (territory['loyalty'] / 100)

        embed = discord.Embed(title=f"Armée de {territory['name']}", color=discord.Color.dark_red())
        embed.add_field(name="Niveau de l'Armée", value=territory['army_level'], inline=True)
        embed.add_field(name="Puissance Militaire (estimée)", value=int(power), inline=True)
        embed.set_footer(text="La puissance dépend du niveau, de la population et de la loyauté.")
        await interaction.response.send_message(embed=embed)

    @army_group.command(name="renforcer", description="Améliore le niveau de votre armée.")
    @app_commands.describe(niveaux="Le nombre de niveaux à acheter.")
    async def reinforce(self, interaction: discord.Interaction, niveaux: int = 1):
        """Upgrades the army level of the character's territory."""
        if niveaux < 1:
            await interaction.response.send_message("Vous devez acheter au moins 1 niveau.", ephemeral=True)
            return

        active_character = get_active_character(interaction.user.id)
        if not active_character:
            await interaction.response.send_message("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        territory = get_character_territory(active_character['id'])
        if not territory:
            await interaction.response.send_message("Votre personnage ne possède pas de territoire.", ephemeral=True)
            return

        cost_per_level = 250 # Example cost
        total_cost = cost_per_level * niveaux

        if active_character['luxium'] < total_cost:
            await interaction.response.send_message(f"Pas assez de Luxium ! Coût total : {total_cost}. Votre solde : {active_character['luxium']}.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        # Deduct cost from character
        new_luxium = active_character['luxium'] - total_cost
        cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_luxium, active_character['id']))

        # Increase army level
        new_army_level = territory['army_level'] + niveaux
        cursor.execute("UPDATE territories SET army_level = ? WHERE id = ?", (new_army_level, territory['id']))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"L'armée de **{territory['name']}** a été renforcée de {niveaux} niveau(x) pour {total_cost} Luxium. Nouveau niveau : **{new_army_level}**.")

    @army_group.command(name="attaquer", description="Lance une attaque contre un autre territoire.")
    @app_commands.describe(cible="Le nom du territoire à attaquer.")
    async def attack(self, interaction: discord.Interaction, cible: str):
        """Launches an attack against another territory."""
        await interaction.response.defer()

        attacker_char = get_active_character(interaction.user.id)
        if not attacker_char:
            await interaction.followup.send("Vous n'avez pas de personnage actif.", ephemeral=True)
            return

        attacker_territory = get_character_territory(attacker_char['id'])
        if not attacker_territory:
            await interaction.followup.send("Votre personnage ne possède pas de territoire pour lancer une attaque.", ephemeral=True)
            return

        defender_territory = get_territory_by_name_global(cible)
        if not defender_territory:
            await interaction.followup.send(f"Le territoire **{cible}** n'existe pas.", ephemeral=True)
            return

        if defender_territory['id'] == attacker_territory['id']:
            await interaction.followup.send("Vous ne pouvez pas vous attaquer vous-même.", ephemeral=True)
            return

        # --- Combat Logic (Simplified) ---
        attacker_power = (attacker_territory['army_level'] * 50) + (attacker_territory['population'] // 10) * (attacker_territory['loyalty'] / 100)
        defender_power = (defender_territory['army_level'] * 50) + (defender_territory['population'] // 10) * (defender_territory['loyalty'] / 100)

        # Add a random element
        attacker_roll = attacker_power + random.randint(1, 20)
        defender_roll = defender_power + random.randint(1, 20)

        result_message = f"**Rapport de Bataille : {attacker_territory['name']} vs. {defender_territory['name']}**\n"
        result_message += f"Puissance d'attaque : {int(attacker_roll)}\n"
        result_message += f"Puissance de défense : {int(defender_roll)}\n\n"

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()

        if attacker_roll > defender_roll:
            result_message += f"**VICTOIRE !** Le territoire de **{defender_territory['name']}** a été conquis !"
            # Transfer ownership
            cursor.execute("UPDATE territories SET owner_character_id = ? WHERE id = ?", (attacker_char['id'], defender_territory['id']))
            # Lower loyalty after conquest
            cursor.execute("UPDATE territories SET loyalty = loyalty - 25 WHERE id = ?", (defender_territory['id'],))
        else:
            result_message += "**DÉFAITE !** Votre armée a été repoussée."
            # Inflict losses (reduce army level)
            new_attacker_level = max(1, attacker_territory['army_level'] - 1)
            cursor.execute("UPDATE territories SET army_level = ? WHERE id = ?", (new_attacker_level, attacker_territory['id']))
            result_message += f"\nLe niveau de votre armée a été réduit à {new_attacker_level}."

        conn.commit()
        conn.close()

        await interaction.followup.send(result_message)


async def setup(bot):
    cog = ArmyCog(bot)
    bot.tree.add_command(cog.army_group)
    await bot.add_cog(cog)
