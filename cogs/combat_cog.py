import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import math
from .utils.db_helpers import get_active_character, get_character_by_name_for_player, get_db_connection

class CombatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="attaquer", description="Attaquez un autre personnage ou PNJ.")
    @app_commands.describe(cible="Le nom de la cible.")
    async def attack(self, interaction: discord.Interaction, cible: str):
        attacker = get_active_character(interaction.user.id)
        if not attacker:
            await interaction.response.send_message("Aucun personnage actif.", ephemeral=True)
            return

        # For now, let's try to find another character by name
        conn = get_db_connection()
        target = conn.execute("SELECT * FROM characters WHERE name = ?", (cible,)).fetchone()
        conn.close()

        if not target:
            await interaction.response.send_message(f"Cible **{cible}** non trouvée.", ephemeral=True)
            return

        if attacker['id'] == target['id']:
            await interaction.response.send_message("Vous ne pouvez pas vous attaquer vous-même.", ephemeral=True)
            return

        await interaction.response.defer()

        # Formula: Impact = (STR + POW + ACC bonus) - DEF adverse
        # ACC bonus: Let's say random between 0 and attacker ACC / 2
        acc_bonus = attacker['acc'] / 2
        impact = (attacker['str'] + attacker['pow'] + acc_bonus) - target['def']

        # Dodging: AGI attacker vs AGI defenseur
        # Simple dodge logic
        dodge_chance = max(0, target['agi'] - attacker['agi']) * 5 # 5% per point difference
        is_dodged = False
        import random
        if random.randint(1, 100) <= dodge_chance:
            is_dodged = True

        result_text = ""
        color = discord.Color.orange()

        if is_dodged:
            result_text = f"**{target['name']}** esquive l'attaque de **{attacker['name']}** grâce à sa vitesse !"
            color = discord.Color.blue()
        else:
            # Damage results
            # ≤ 0 → blocage total
            # 1–10 → contusion
            # 11–25 → blessure sérieuse
            # 26–50 → fracture
            # 50+ → dégâts critiques

            damage = max(0, int(impact))

            if damage <= 0:
                result_text = f"**{target['name']}** bloque totalement l'attaque. Aucun dégât."
                damage = 0
            elif 1 <= damage <= 10:
                result_text = f"**{target['name']}** subit une contusion."
            elif 11 <= damage <= 25:
                result_text = f"**{target['name']}** subit une blessure sérieuse !"
            elif 26 <= damage <= 50:
                result_text = f"**{target['name']}** subit une fracture ! L'impact est brutal."
            else:
                result_text = f"**DÉGÂTS CRITIQUES !** **{target['name']}** est gravement touché."

            # Update target HP
            new_hp = max(0, target['hp'] - damage)
            conn = get_db_connection()
            conn.execute("UPDATE characters SET hp = ? WHERE id = ?", (new_hp, target['id']))
            conn.commit()
            conn.close()

            result_text += f"\nImpact : {damage} | PV restants : {new_hp}/{target['max_hp']}"

        embed = discord.Embed(title="Combat Aetheris", description=result_text, color=color)
        embed.set_footer(text=f"{attacker['name']} vs {target['name']}")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CombatCog(bot))
