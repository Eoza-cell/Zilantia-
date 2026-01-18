import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# Helper function to get the active character, now including zone info
def get_active_character_with_zone(user_id):
    conn = sqlite3.connect('zilantia.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id, c.name, c.level, c.xp, c.luxium,
            o.name AS origin_name,
            f.name AS faction_name,
            z.id AS zone_id, z.name AS zone_name, z.description AS zone_description
        FROM characters c
        JOIN players p ON c.player_id = p.id
        JOIN zones z ON c.current_zone_id = z.id
        LEFT JOIN origins o ON c.origin_id = o.id
        LEFT JOIN factions f ON c.faction_id = f.id
        WHERE p.user_id = ? AND p.active_character_id = c.id
    """, (user_id,))
    character_data = cursor.fetchone()
    conn.close()
    if character_data:
        return {
            "id": character_data[0], "name": character_data[1], "level": character_data[2],
            "xp": character_data[3], "luxium": character_data[4], "origin": character_data[5],
            "faction": character_data[6], "zone_id": character_data[7], "zone_name": character_data[8],
            "zone_description": character_data[9]
        }
    return None

class ExplorationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ou-suis-je", description="Affiche les informations sur votre zone actuelle.")
    async def where_am_i(self, interaction: discord.Interaction):
        character = get_active_character_with_zone(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage.", ephemeral=True)
            return

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()
        # Find NPCs in the current zone (case-insensitive)
        cursor.execute("SELECT name FROM npcs WHERE lower(zone) = ?", (character['zone_name'].lower(),))
        npcs_in_zone = [row[0] for row in cursor.fetchall()]
        conn.close()

        embed = discord.Embed(
            title=f"📍 {character['zone_name']}",
            description=character['zone_description'],
            color=discord.Color.dark_teal()
        )
        embed.set_image(url="https://pollinations.ai/p/conceptual_isometric_world_of_pollinations_ai_surreal_hyperrealistic_digital_garden")
        embed.set_author(name=f"Emplacement de {character['name']}")

        if npcs_in_zone:
            embed.add_field(name="Personnages rencontrés", value="\n".join(npcs_in_zone), inline=False)
        else:
            embed.add_field(name="Personnages rencontrés", value="Cette zone semble déserte.", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="explorer", description="Découvrez les zones accessibles depuis votre position.")
    async def explore(self, interaction: discord.Interaction):
        character = get_active_character_with_zone(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage.", ephemeral=True)
            return

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()
        # Get all zones the character can potentially travel to (not the current one)
        cursor.execute("SELECT name, description, required_level FROM zones WHERE id != ?", (character['zone_id'],))
        available_zones = cursor.fetchall()
        conn.close()

        embed = discord.Embed(
            title="🗺️ Exploration des environs",
            description=f"Depuis la {character['zone_name']}, voici les chemins qui s'offrent à vous :",
            color=discord.Color.blurple()
        )

        if not available_zones:
            embed.description += "\n\nIl semble n'y avoir aucune autre destination connue pour le moment."
        else:
            for name, desc, level in available_zones:
                accessible = "✅" if character['level'] >= level else "❌"
                embed.add_field(
                    name=f"{name} (Niveau {level} requis) {accessible}",
                    value=f"*{desc}*",
                    inline=False
                )

        embed.set_footer(text="Utilisez /voyager <destination> pour vous déplacer.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="voyager", description="Se déplacer vers une nouvelle zone.")
    @app_commands.describe(destination="Le nom de la zone où vous voulez aller.")
    async def travel(self, interaction: discord.Interaction, destination: str):
        character = get_active_character_with_zone(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage.", ephemeral=True)
            return

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, required_level FROM zones WHERE lower(name) = ?", (destination.lower(),))
        target_zone = cursor.fetchone()

        if not target_zone:
            conn.close()
            await interaction.response.send_message(f"La destination '{destination}' est inconnue.", ephemeral=True)
            return

        target_id, target_name, target_level = target_zone

        if target_id == character['zone_id']:
            conn.close()
            await interaction.response.send_message("Vous êtes déjà dans cette zone.", ephemeral=True)
            return

        if character['level'] < target_level:
            conn.close()
            await interaction.response.send_message(f"Votre niveau est trop faible. La zone '{target_name}' requiert le niveau {target_level}.", ephemeral=True)
            return

        # Update character's location
        cursor.execute("UPDATE characters SET current_zone_id = ? WHERE id = ?", (target_id, character['id']))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"**{character['name']}** a voyagé vers **{target_name}**.")

async def setup(bot):
    await bot.add_cog(ExplorationCog(bot))
