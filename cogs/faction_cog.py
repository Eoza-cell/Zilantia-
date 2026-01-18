import discord
from discord.ext import commands
from discord import app_commands
from .utils.db_helpers import get_active_character, get_db_connection, get_all_factions

class FactionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class FactionSelectionView(discord.ui.View):
        def __init__(self, character_id: int):
            super().__init__(timeout=180)
            self.character_id = character_id
            self.add_item(self.FactionSelect())

        class FactionSelect(discord.ui.Select):
            def __init__(self):
                factions = get_all_factions()
                options = [
                    discord.SelectOption(label=faction['name'], value=str(faction['id']))
                    for faction in factions
                ]
                super().__init__(placeholder="Choisissez votre faction...", min_values=1, max_values=1, options=options)

            async def callback(self, interaction: discord.Interaction):
                faction_id = int(self.values[0])
                character_id = self.view.character_id

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE characters SET faction_id = ? WHERE id = ?",
                    (faction_id, character_id)
                )
                conn.commit()
                conn.close()

                selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), "N/A")

                for item in self.view.children:
                    item.disabled = True

                await interaction.response.edit_message(
                    content=f"Vous avez rejoint la faction **{selected_label}** !",
                    view=self.view
                )

    faction_group = app_commands.Group(name="faction", description="Gérez votre faction.")

    @faction_group.command(name="join", description="Rejoignez une faction.")
    async def join(self, interaction: discord.Interaction):
        character = get_active_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("Vous devez d'abord créer un personnage avec `/start`.", ephemeral=True)
            return

        if character['faction_id']:
            await interaction.response.send_message("Votre personnage a déjà rejoint une faction.", ephemeral=True)
            return

        view = self.FactionSelectionView(character_id=character['id'])
        await interaction.response.send_message("Choisissez la faction que vous souhaitez rejoindre :", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(FactionCog(bot))
