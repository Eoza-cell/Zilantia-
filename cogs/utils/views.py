import discord
from discord import ui
import sqlite3
from .db_helpers import get_player_by_discord_id, create_player, get_character_by_name_for_player

class CharacterCreationModal(ui.Modal, title="Création de Personnage"):
    nom = ui.TextInput(label="Nom du Personnage", placeholder="Entrez le nom de votre personnage")

    async def on_submit(self, interaction: discord.Interaction):
        player = get_player_by_discord_id(interaction.user.id)
        if not player:
            player = create_player(interaction.user.id, interaction.user.name)

        if get_character_by_name_for_player(player['id'], self.nom.value):
            await interaction.response.send_message(f"Vous avez déjà un personnage nommé **{self.nom.value}**.", ephemeral=True)
            return

        conn = sqlite3.connect('arcanes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO characters (player_id, name) VALUES (?, ?)", (player['id'], self.nom.value))
        new_character_id = cursor.lastrowid

        if not player['active_character_id']:
            cursor.execute("UPDATE players SET active_character_id = ? WHERE id = ?", (new_character_id, player['id']))

        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Votre personnage **{self.nom.value}** a été créé. Vous pouvez maintenant utiliser la commande `/menu`.", ephemeral=True)


class CreateCharacterView(ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @ui.button(label="Créer un Personnage", style=discord.ButtonStyle.success)
    async def create_character(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CharacterCreationModal())
