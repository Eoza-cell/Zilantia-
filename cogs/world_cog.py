import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

# --- Helper to get character by name ---
def get_character_by_name_global(character_name: str):
    conn = sqlite3.connect('arcanes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters WHERE name = ?", (character_name,))
    character = cursor.fetchone()
    conn.close()
    return character

class WorldCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Events Subgroup ---
    event_group = app_commands.Group(name="event", description="Gère les événements mondiaux.", default_permissions=discord.Permissions(administrator=True))

    @event_group.command(name="create", description="Crée un nouvel événement mondial.")
    @app_commands.describe(nom="Le nom de l'événement.", type="Le type (ex: Boss, Rébellion, Artefact).", description="Une courte description de l'événement.")
    async def event_create(self, interaction: discord.Interaction, nom: str, type: str, description: str):
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO world_events (name, type, description) VALUES (?, ?, ?)", (nom, type, description))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"L'événement mondial **{nom}** ({type}) a été créé et est maintenant actif.")

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
            await interaction.response.send_message(f"Aucun événement actif nommé **{nom}** n'a été trouvé.", ephemeral=True)
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
            await interaction.response.send_message("Il n'y a aucun événement mondial actif en ce moment.", ephemeral=True)
            return

        embed = discord.Embed(title="Événements Mondiaux Actifs", color=discord.Color.orange())
        for event in events:
            embed.add_field(name=f"**{event['name']}** ({event['type']})", value=event['description'], inline=False)
        await interaction.response.send_message(embed=embed)

    # --- Artifacts Subgroup ---
    artefact_group = app_commands.Group(name="artefact", description="Gère les artefacts rares.", default_permissions=discord.Permissions(administrator=True))

    @artefact_group.command(name="create", description="Crée un nouvel artefact dans le monde.")
    @app_commands.describe(nom="Le nom de l'artefact.", rarete="Sa rareté (ex: Commun, Rare, Légendaire).", effet="La description de son pouvoir.")
    async def artefact_create(self, interaction: discord.Interaction, nom: str, rarete: str, effet: str):
        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO artefacts (name, rarity, effect) VALUES (?, ?, ?)", (nom, rarete, effet))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"L'artefact **{nom}** ({rarete}) a été créé.")

    @artefact_group.command(name="give", description="Donne un artefact à un personnage.")
    @app_commands.describe(nom_artefact="Le nom de l'artefact à donner.", nom_personnage="Le personnage qui le recevra.")
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

async def setup(bot):
    cog = WorldCog(bot)
    bot.tree.add_command(cog.event_group)
    bot.tree.add_command(cog.artefact_group)
    await bot.add_cog(cog)
