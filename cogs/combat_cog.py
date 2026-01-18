import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import requests
import os

# Helper function to get full character stats including combat and zone info
def get_character_full_stats(user_id):
    conn = sqlite3.connect('zilantia.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id, c.name, c.level, c.xp, c.luxium, c.hp, c.attack,
            o.name AS origin_name,
            f.name AS faction_name,
            z.id AS zone_id, z.name AS zone_name
        FROM characters c
        JOIN players p ON c.player_id = p.id
        JOIN zones z ON c.current_zone_id = z.id
        LEFT JOIN origins o ON c.origin_id = o.id
        LEFT JOIN factions f ON c.faction_id = f.id
        WHERE p.user_id = ? AND p.active_character_id = c.id
    """, (user_id,))
    data = cursor.fetchone()
    conn.close()
    if data:
        return {
            "id": data[0], "name": data[1], "level": data[2], "xp": data[3],
            "luxium": data[4], "hp": data[5], "attack": data[6], "origin": data[7],
            "faction": data[8], "zone_id": data[9], "zone_name": data[10]
        }
    return None

class CombatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("POLLINATION_API_KEY")

    boss_group = app_commands.Group(name="boss", description="Commandes liées aux boss du monde.")

    @boss_group.command(name="inspecter", description="Inspecte le boss de votre zone actuelle.")
    async def inspect_boss(self, interaction: discord.Interaction):
        character = get_character_full_stats(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage.", ephemeral=True)
            return

        await interaction.response.defer()

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, description, hp, attack, required_level
            FROM bosses
            WHERE zone_id = ? AND is_active = 1
        """, (character['zone_id'],))
        boss = cursor.fetchone()
        conn.close()

        if not boss:
            await interaction.followup.send("Il n'y a aucun boss actif dans cette zone.", ephemeral=True)
            return

        name, description, hp, attack, level = boss

        # --- Generate Image ---
        prompt = f"epic fantasy boss, {description.replace('.', '')}, dark fantasy art, cinematic lighting"
        image_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}"
        if self.api_key:
            image_url += f"?apikey={self.api_key}"

        embed = discord.Embed(
            title=f" menace détectée : {name}",
            description=description,
            color=discord.Color.dark_red()
        )
        embed.set_image(url=image_url)
        embed.set_author(name=f"Boss de la zone : {character['zone_name']}")
        embed.add_field(name="Niveau Requis", value=level, inline=True)
        embed.add_field(name="Points de Vie", value=hp, inline=True)
        embed.add_field(name="Attaque", value=attack, inline=True)
        embed.set_footer(text="Utilisez /boss attaquer pour engager le combat.")

        await interaction.followup.send(embed=embed)

    @boss_group.command(name="attaquer", description="Engage le combat avec le boss de la zone.")
    async def attack_boss(self, interaction: discord.Interaction):
        character = get_character_full_stats(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage.", ephemeral=True)
            return

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, hp, attack, required_level
            FROM bosses
            WHERE zone_id = ? AND is_active = 1
        """, (character['zone_id'],))
        boss_data = cursor.fetchone()

        if not boss_data:
            conn.close()
            await interaction.response.send_message("Il n'y a aucun boss à combattre dans cette zone.", ephemeral=True)
            return

        boss_id, boss_name, boss_hp, boss_attack, boss_level = boss_data

        if character['level'] < boss_level:
            conn.close()
            await interaction.response.send_message(f"Votre niveau {character['level']} est trop faible pour affronter {boss_name} (Niveau {boss_level} requis).", ephemeral=True)
            return

        await interaction.response.defer()

        # --- Combat Simulation ---
        char_hp = character['hp']
        combat_log = []
        turn = 1

        while char_hp > 0 and boss_hp > 0:
            # Player attacks
            boss_hp -= character['attack']
            combat_log.append(f"**Tour {turn}:** {character['name']} inflige **{character['attack']}** dégâts au {boss_name}. (PV restants du boss: {max(0, boss_hp)})")
            if boss_hp <= 0:
                break

            # Boss attacks
            char_hp -= boss_attack
            combat_log.append(f"**Tour {turn}:** {boss_name} riposte et inflige **{boss_attack}** dégâts. (Vos PV restants: {max(0, char_hp)})")

            turn += 1

        # --- Combat Result ---
        embed = discord.Embed(title=f"⚔️ Combat terminé : {character['name']} vs {boss_name}")

        if char_hp > 0: # Player wins
            reward_xp = boss_level * 10
            reward_luxium = boss_level * 5

            cursor.execute("UPDATE characters SET xp = xp + ?, luxium = luxium + ? WHERE id = ?", (reward_xp, reward_luxium, character['id']))
            cursor.execute("UPDATE bosses SET is_active = 0 WHERE id = ?", (boss_id,))
            conn.commit()

            embed.color = discord.Color.green()
            embed.description = f"**Victoire !** Vous avez terrassé le {boss_name}."
            embed.add_field(name="Récompenses", value=f"✨ +{reward_xp} XP\n💎 +{reward_luxium} Luxium", inline=False)

        else: # Player loses
            penalty_luxium = 15
            new_luxium = max(0, character['luxium'] - penalty_luxium)
            cursor.execute("UPDATE characters SET luxium = ? WHERE id = ?", (new_luxium, character['id']))
            conn.commit()

            embed.color = discord.Color.red()
            embed.description = f"**Défaite !** Vous avez été vaincu par le {boss_name}."
            embed.add_field(name="Pénalité", value=f"💎 -{penalty_luxium} Luxium", inline=False)

        conn.close()

        log_string = "\n".join(combat_log)
        if len(log_string) > 1024:
            log_string = log_string[:1020] + "..."
        embed.add_field(name="Journal de combat", value=log_string, inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CombatCog(bot))
