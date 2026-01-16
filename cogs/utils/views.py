import discord

class CreateCharacterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Créer un Personnage", style=discord.ButtonStyle.success, custom_id="create_character_button")
    async def create_character(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Provides guidance on how to create a character when the button is clicked.
        """
        await interaction.response.send_message(
            "Parfait ! Pour créer votre personnage, utilisez la commande `/start` et donnez-lui un nom. Par exemple : `/start nom: Arthur`",
            ephemeral=True
        )
        # Visually disable the button for the user who clicked it.
        button.disabled = True
        button.label = "Instruction envoyée"
        await interaction.edit_original_response(view=self)
        self.stop()
