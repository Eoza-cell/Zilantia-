import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class SyncCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Synchronise les rangs du jeu avec les rôles Discord.")
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        """Synchronizes in-game ranks with Discord roles for all members."""
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        # --- Mapping of in-game ranks to Discord role names ---
        # IMPORTANT: Role names on your Discord server MUST EXACTLY match these names (case-sensitive).
        rank_to_role_name = {
            'F': 'F', 'E': 'E', 'D': 'D', 'C': 'C',
            'B': 'B', 'A': 'A', 'S': 'S', 'SS': 'SS'
        }

        all_rank_roles_on_server = {role.name: role for role in guild.roles if role.name in rank_to_role_name.values()}
        all_rank_roles_set = set(all_rank_roles_on_server.values())

        logs = []
        updated_members = 0

        conn = sqlite3.connect('arcanes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Iterate through all members in the server
        for member in guild.members:
            if member.bot:
                continue

            # Get the member's active character
            cursor.execute("""
                SELECT c.rang FROM characters c
                JOIN players p ON c.player_id = p.id
                WHERE p.user_id = ? AND p.active_character_id = c.id
            """, (member.id,))
            character = cursor.fetchone()

            current_rank_roles = set(member.roles) & all_rank_roles_set
            target_role = None

            if character:
                target_role_name = rank_to_role_name.get(character['rang'])
                if target_role_name:
                    target_role = all_rank_roles_on_server.get(target_role_name)

            roles_to_add = []
            roles_to_remove = list(current_rank_roles) # Copy to list for removal

            if target_role and target_role not in current_rank_roles:
                roles_to_add.append(target_role)
                if target_role in roles_to_remove:
                    roles_to_remove.remove(target_role)

            if roles_to_add or roles_to_remove:
                try:
                    await member.add_roles(*roles_to_add, reason="Synchronisation des rangs Arcanes")
                    await member.remove_roles(*roles_to_remove, reason="Synchronisation des rangs Arcanes")
                    logs.append(f"✅ {member.display_name}: Rôle mis à jour vers '{target_role.name if target_role else 'Aucun'}'.")
                    updated_members += 1
                except discord.Forbidden:
                    logs.append(f"❌ {member.display_name}: Permissions manquantes pour gérer les rôles.")
                except Exception as e:
                    logs.append(f"🔥 {member.display_name}: Erreur inattendue - {e}")

        conn.close()

        if not logs:
            await interaction.followup.send("Aucun membre n'avait besoin d'une mise à jour de rôle.", ephemeral=True)
            return

        # Sending logs
        log_message = f"**Synchronisation des Rôles Terminée !**\n{updated_members} membre(s) mis à jour.\n\n"
        log_message += "\n".join(logs)

        # Discord has a 2000 character limit per message
        if len(log_message) > 2000:
            await interaction.followup.send(f"**Synchronisation des Rôles Terminée !**\n{updated_members} membre(s) mis à jour. Les logs sont trop longs pour être affichés ici.", ephemeral=True)
        else:
            await interaction.followup.send(log_message, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SyncCog(bot))
