import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import requests
import os

# Helper function to get the active character
def get_active_character(user_id):
    conn = sqlite3.connect('zilantia.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.name, c.level, c.xp, c.luxium, o.name, f.name
        FROM characters c
        JOIN players p ON c.player_id = p.id
        LEFT JOIN origins o ON c.origin_id = o.id
        LEFT JOIN factions f ON c.faction_id = f.id
        WHERE p.user_id = ? AND p.active_character_id = c.id
    """, (user_id,))
    character = cursor.fetchone()
    conn.close()
    if character:
        return {
            "id": character[0], "name": character[1], "level": character[2],
            "xp": character[3], "luxium": character[4], "origin": character[5],
            "faction": character[6]
        }
    return None

# --- UI Views for Quest Interaction ---
class QuestAcceptView(discord.ui.View):
    def __init__(self, character_id, available_quests):
        super().__init__(timeout=180)
        self.character_id = character_id

        for quest in available_quests:
            quest_id, quest_title = quest
            button = discord.ui.Button(label=f"Accepter : {quest_title}", custom_id=f"accept_quest_{quest_id}", style=discord.ButtonStyle.success)
            button.callback = self.accept_quest_callback
            self.add_item(button)

    async def accept_quest_callback(self, interaction: discord.Interaction):
        quest_id = int(interaction.data['custom_id'].split('_')[-1])

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()

        try:
            # Check if the character already has the quest
            cursor.execute("SELECT status FROM character_quests WHERE character_id = ? AND quest_id = ?", (self.character_id, quest_id))
            if cursor.fetchone():
                await interaction.response.send_message("Vous avez déjà cette quête dans votre journal.", ephemeral=True)
                return

            # Add quest to character's log
            cursor.execute("INSERT INTO character_quests (character_id, quest_id, status) VALUES (?, ?, ?)", (self.character_id, quest_id, 'active'))
            conn.commit()

            cursor.execute("SELECT title FROM quests WHERE id = ?", (quest_id,))
            quest_title = cursor.fetchone()[0]

            await interaction.response.send_message(f"**Nouvelle quête acceptée :** {quest_title}\nConsultez votre journal avec `/quete`.", ephemeral=True)

            # Disable the button after accepting
            for item in self.children:
                if item.custom_id == interaction.data['custom_id']:
                    item.disabled = True
                    item.label = f"✔️ {item.label}"
                    item.style = discord.ButtonStyle.secondary
            await interaction.message.edit(view=self)

        except sqlite3.Error as e:
            await interaction.response.send_message(f"Une erreur de base de données est survenue : {e}", ephemeral=True)
        finally:
            conn.close()

class QuestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("POLLINATION_API_KEY")

    @app_commands.command(name="parler", description="Parler à un personnage non-joueur (PNJ).")
    @app_commands.describe(nom_pnj="Le nom du PNJ avec qui vous voulez parler.")
    async def parler(self, interaction: discord.Interaction, nom_pnj: str):
        """Allows a player to talk to an NPC."""
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage avec `/creer_personnage`.", ephemeral=True)
            return

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, zone, dialogue_prompt FROM npcs WHERE lower(name) = ?", (nom_pnj.lower(),))
        npc = cursor.fetchone()

        if not npc:
            await interaction.response.send_message(f"Aucun PNJ nommé '{nom_pnj}' n'a été trouvé.", ephemeral=True)
            conn.close()
            return

        npc_id, npc_name, npc_description, npc_zone, dialogue_prompt = npc

        # --- Generate dynamic dialogue using Pollinations.ai ---
        await interaction.response.defer()
        dialogue = "Le PNJ vous regarde sans dire un mot." # Default
        try:
            url = f"https://gen.pollinations.ai/text/{dialogue_prompt.replace(' ', '%20')}"
            if self.api_key:
                url += f"?apikey={self.api_key}"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            dialogue = data.get("text", dialogue)
        except requests.exceptions.RequestException:
            dialogue = dialogue_prompt

        embed = discord.Embed(
            title=f"Dialogue avec {npc_name}",
            description=f"*Vous rencontrez {npc_name} dans la zone : {npc_zone}.*",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.avatar.url)
        embed.add_field(name=f"Description du PNJ", value=npc_description, inline=False)
        embed.add_field(name="Dialogue", value=f"> {dialogue}", inline=False)

        # --- Check for available quests ---
        cursor.execute("""
            SELECT q.id, q.title
            FROM quests q
            WHERE q.npc_id = ? AND q.required_level <= ?
            AND NOT EXISTS (
                SELECT 1 FROM character_quests cq
                WHERE cq.quest_id = q.id AND cq.character_id = ?
            )
        """, (npc_id, character['level'], character['id']))
        available_quests = cursor.fetchall()

        view = QuestAcceptView(character['id'], available_quests) if available_quests else None

        if view:
            embed.add_field(name="Quêtes disponibles", value="Ce PNJ a des missions pour vous.", inline=False)

        await interaction.followup.send(embed=embed, view=view)
        conn.close()

    @app_commands.command(name="quete", description="Consultez votre journal de quêtes.")
    async def quete(self, interaction: discord.Interaction):
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage avec `/creer_personnage`.", ephemeral=True)
            return

        conn = sqlite3.connect('zilantia.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT q.title, q.description, cq.status
            FROM character_quests cq
            JOIN quests q ON cq.quest_id = q.id
            WHERE cq.character_id = ?
        """, (character['id'],))

        quests = cursor.fetchall()
        conn.close()

        embed = discord.Embed(title=f"Journal de quêtes de {character['name']}", color=discord.Color.dark_green())

        if not quests:
            embed.description = "Vous n'avez aucune quête en cours."
        else:
            active_quests = [q for q in quests if q[2] == 'active']
            completed_quests = [q for q in quests if q[2] == 'terminée']

            if active_quests:
                embed.add_field(
                    name="Quêtes Actives",
                    value="\n".join([f"**{q[0]}**: {q[1]}" for q in active_quests]),
                    inline=False
                )
            if completed_quests:
                embed.add_field(
                    name="Quêtes Terminées",
                    value="\n".join([f"**{q[0]}**: *Terminée*" for q in completed_quests]),
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(QuestCog(bot))
