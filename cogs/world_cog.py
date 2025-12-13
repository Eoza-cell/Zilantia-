import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from .utils.db_helpers import get_character_by_name_global

class WorldCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    event_group = app_commands.Group(name="event", description="Gère les événements mondiaux.", default_permissions=discord.Permissions(administrator=True))

    @event_group.command(name="create", description="Crée un nouvel événement mondial.")
    @app_commands.describe(nom="Le nom de l'événement.", type="Le type (ex: Boss, Rébellion, Artefact, SS).", description="Une courte description.")
    async def event_create(self, interaction: discord.Interaction, nom: str, type: str, description: str):
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO world_events (name, type, description) VALUES (?, ?, ?)", (nom, type, description))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"L'événement mondial **{nom}** ({type}) est maintenant actif.")

    @event_group.command(name="end", description="Termine un événement mondial actif.")
    @app_commands.describe(nom="Le nom de l'événement à terminer.")
    async def event_end(self, interaction: discord.Interaction, nom: str):
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE world_events SET is_active = FALSE WHERE name = ? AND is_active = TRUE", (nom,))
        if cursor.rowcount > 0:
            conn.commit()
            await interaction.response.send_message(f"L'événement **{nom}** a été terminé.")
        else:
            await interaction.response.send_message(f"Aucun événement actif nommé **{nom}** trouvé.", ephemeral=True)
        conn.close()

    @event_group.command(name="list", description="Affiche tous les événements mondiaux actifs.")
    async def event_list(self, interaction: discord.Interaction):
        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM world_events WHERE is_active = TRUE")
        events = cursor.fetchall()
        conn.close()

        if not events:
            await interaction.response.send_message("Aucun événement mondial actif.", ephemeral=True)
            return

        embed = discord.Embed(title="Événements Mondiaux Actifs", color=discord.Color.orange())
        for event in events:
            embed.add_field(name=f"**{event['name']}** ({event['type']})", value=event['description'], inline=False)
        await interaction.response.send_message(embed=embed)

    artefact_group = app_commands.Group(name="artefact", description="Gère les artefacts rares.", default_permissions=discord.Permissions(administrator=True))

    @artefact_group.command(name="create", description="Crée un nouvel artefact.")
    @app_commands.describe(nom="Le nom de l'artefact.", rarete="Sa rareté.", effet="La description de son pouvoir.")
    async def artefact_create(self, interaction: discord.Interaction, nom: str, rarete: str, effet: str):
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO artefacts (name, rarity, effect) VALUES (?, ?, ?)", (nom, rarete, effet))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"L'artefact **{nom}** ({rarete}) a été créé.")

    @artefact_group.command(name="delete", description="Supprime un artefact du monde.")
    @app_commands.describe(nom="Le nom exact de l'artefact à supprimer.")
    async def artefact_delete(self, interaction: discord.Interaction, nom: str):
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM artefacts WHERE name = ?", (nom,))

        if cursor.rowcount > 0:
            conn.commit()
            await interaction.response.send_message(f"L'artefact **{nom}** a été supprimé.")
        else:
            await interaction.response.send_message(f"Aucun artefact nommé **{nom}** trouvé.", ephemeral=True)
        conn.close()

    @artefact_group.command(name="give", description="Donne un artefact à un personnage.")
    @app_commands.describe(nom_artefact="Le nom de l'artefact.", nom_personnage="Le personnage qui le recevra.")
    async def artefact_give(self, interaction: discord.Interaction, nom_artefact: str, nom_personnage: str):
        character = get_character_by_name_global(nom_personnage)
        if not character:
            await interaction.response.send_message(f"Personnage **{nom_personnage}** introuvable.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM artefacts WHERE name = ?", (nom_artefact,))
        artefact = cursor.fetchone()

        if not artefact:
            await interaction.response.send_message(f"Artefact **{nom_artefact}** introuvable.", ephemeral=True)
            conn.close()
            return

        cursor.execute("UPDATE artefacts SET owner_character_id = ? WHERE id = ?", (character['id'], artefact['id']))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"L'artefact **{nom_artefact}** a été donné à **{nom_personnage}**.")

    @app_commands.command(name="artefacts", description="Affiche la liste de tous les artefacts du monde.")
    async def list_artefacts(self, interaction: discord.Interaction):
        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT a.name, a.rarity, a.effect, c.name as owner_name FROM artefacts a LEFT JOIN characters c ON a.owner_character_id = c.id")
        artefacts = cursor.fetchall()
        conn.close()

        if not artefacts:
            await interaction.response.send_message("Il n'y a aucun artefact connu dans ce monde.", ephemeral=True)
            return

        embed = discord.Embed(title="Artefacts de l'Ère des Arcanes", color=discord.Color.purple())
        for artefact in artefacts:
            owner = artefact['owner_name'] if artefact['owner_name'] else "Personne"
            embed.add_field(name=f"**{artefact['name']}** [{artefact['rarity']}]", value=f"_{artefact['effect']}_\n**Possédé par :** {owner}", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(WorldCog(bot))
