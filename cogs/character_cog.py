import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from .utils.db_helpers import get_player_by_discord_id, create_player, get_character_by_name_for_player, get_player_characters, get_all_origins, get_active_character, get_db_connection
from .utils.views import CreateCharacterView

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- UI View for Origin Selection ---
    class OriginSelectionView(discord.ui.View):
        def __init__(self, player_id: int, character_name: str, set_as_active: bool = True):
            super().__init__(timeout=180)
            self.player_id = player_id
            self.character_name = character_name
            self.set_as_active = set_as_active
            self.add_item(self.OriginSelect())

        class OriginSelect(discord.ui.Select):
            def __init__(self):
                origins = get_all_origins()
                if not origins:
                    options = [discord.SelectOption(label="Erreur: Aucune origine trouvée", value="error")]
                else:
                    options = [
                        discord.SelectOption(label=origin['name'], value=str(origin['id']))
                        for origin in origins
                    ]
                super().__init__(placeholder="Choisissez votre origine...", min_values=1, max_values=1, options=options)

            async def callback(self, interaction: discord.Interaction):
                if self.values[0] == "error":
                    await interaction.response.edit_message(content="Impossible de créer le personnage. Contactez un administrateur.", view=None)
                    return

                player_id = self.view.player_id
                character_name = self.view.character_name
                origin_id = int(self.values[0])

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO characters (player_id, name, origin_id) VALUES (?, ?, ?)",
                    (player_id, character_name, origin_id)
                )
                new_character_id = cursor.lastrowid

                if self.view.set_as_active:
                    cursor.execute(
                        "UPDATE players SET active_character_id = ? WHERE id = ?",
                        (new_character_id, player_id)
                    )
                conn.commit()
                conn.close()

                selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), "N/A")

                # Disable the view after selection
                for item in self.view.children:
                    item.disabled = True

                await interaction.response.edit_message(
                    content=f"Votre personnage **{character_name}** a été créé avec l'origine **{selected_label}**. Utilisez `/profile` pour le voir.",
                    view=self.view
                )

    @app_commands.command(name="start", description="Commencez l'aventure et créez votre premier personnage.")
    @app_commands.describe(nom="Le nom de votre premier personnage.")
    async def start(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        characters = get_player_characters(player['id'])
        if characters:
            await interaction.response.send_message("Vous avez déjà un personnage. Utilisez `/character create` pour en créer un autre.", ephemeral=True)
            return

        view = self.OriginSelectionView(player_id=player['id'], character_name=nom, set_as_active=True)
        await interaction.response.send_message("Votre voyage commence. Choisissez l'origine de votre personnage :", view=view, ephemeral=True)

    character_group = app_commands.Group(name="character", description="Gérez vos personnages secondaires.")

    @character_group.command(name="create", description="Crée un nouveau personnage.")
    async def create(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        if get_character_by_name_for_player(player['id'], nom):
            await interaction.response.send_message(f"Vous avez déjà un personnage nommé **{nom}**.", ephemeral=True)
            return

        # Determine if the new character should be set as active
        should_set_active = not bool(player['active_character_id'])

        view = self.OriginSelectionView(player_id=player['id'], character_name=nom, set_as_active=should_set_active)
        await interaction.response.send_message("Choisissez l'origine de votre nouveau personnage :", view=view, ephemeral=True)

    @character_group.command(name="switch", description="Changez de personnage actif.")
    async def switch(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        target_character = get_character_by_name_for_player(player['id'], nom)
        if not target_character:
            await interaction.response.send_message(f"Vous n'avez pas de personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (target_character['id'], player['id']))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Votre personnage actif est maintenant **{nom}**.")

    @character_group.command(name="delete", description="Supprime l'un de vos personnages.")
    @app_commands.describe(nom="Le nom exact du personnage à supprimer.")
    async def delete(self, interaction: discord.Interaction, nom: str):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez aucun personnage à supprimer.", ephemeral=True)
            return

        character_to_delete = get_character_by_name_for_player(player['id'], nom)
        if not character_to_delete:
            await interaction.response.send_message(f"Vous n'avez pas de personnage nommé **{nom}**.", ephemeral=True)
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM territories WHERE owner_character_id = ?", (character_to_delete['id'],))
        if cursor.fetchone():
            await interaction.response.send_message(f"**{nom}** possède un territoire et ne peut être supprimé.", ephemeral=True)
            conn.close()
            return

        if player['active_character_id'] == character_to_delete['id']:
            cursor.execute("UPDATE players SET active_character_id = NULL WHERE id = ?", (player['id'],))
        cursor.execute("DELETE FROM characters WHERE id = ?", (character_to_delete['id'],))
        cursor.execute("UPDATE artefacts SET owner_character_id = NULL WHERE owner_character_id = ?", (character_to_delete['id'],))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Le personnage **{nom}** a été supprimé.")

    @character_group.command(name="list", description="Affiche la liste de vos personnages.")
    async def list(self, interaction: discord.Interaction):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        characters = get_player_characters(player['id'])
        if not characters:
            await interaction.response.send_message("Vous n'avez pas encore de personnage.", ephemeral=True)
            return

        active_char_id = player['active_character_id']
        description = ""
        for char in characters:
            status = " (Actif)" if char['id'] == active_char_id else ""
            description += f"- **{char['name']}**{status}\n"

        embed = discord.Embed(title=f"Personnages de {interaction.user.name}", description=description, color=discord.Color.dark_green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="profile", description="Affiche le profil de votre personnage actif.")
    async def profile(self, interaction: discord.Interaction):
        character = get_active_character(interaction.user.id)
        if not character:
            # Using a more user-friendly view for users without characters
            view = CreateCharacterView()
            await interaction.response.send_message(
                "Vous n'avez pas encore de personnage. Souhaitez-vous en créer un maintenant ?",
                view=view,
                ephemeral=True
            )
            return

        embed = discord.Embed(title=f"Profil de {character['name']}", color=discord.Color.dark_purple())
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)

        # Main stats
        embed.add_field(name="Origine", value=character['origin_name'], inline=True)
        embed.add_field(name="Faction", value=character['faction_name'] if character['faction_name'] else "Aucune", inline=True)
        embed.add_field(name="Niveau", value=character['level'], inline=True)
        embed.add_field(name="XP", value=f"{character['xp']}", inline=True)
        embed.add_field(name="💰 Luxium", value=f"{character['luxium']}", inline=True)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
