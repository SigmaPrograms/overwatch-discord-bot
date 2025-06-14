import discord, json, asyncio
from discord import app_commands, Interaction
from discord.ext import commands
from core.database import db
from core.embeds import session_embed
from core.models import GAME_MODES

class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ───── /create-session ─────────────────────────────
    @app_commands.command(name="create-session")
    @app_commands.describe(game_mode="5v5, 6v6, Stadium",
                           description="Optional note",
                           max_rank_diff="Highest SR delta allowed")
    async def create_session(self, interaction: Interaction,
                             game_mode: str,
                             scheduled_time: str,
                             timezone: str,
                             description: str | None = None,
                             max_rank_diff: int | None = None):
        """Owner schedules a new session."""
        # Validation & parsing omitted for brevity
        await db.execute(
            """INSERT INTO sessions (creator_id, guild_id, channel_id,
               game_mode, scheduled_time, timezone, description,
               max_rank_diff, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')""",
            interaction.user.id, interaction.guild_id, interaction.channel_id,
            game_mode, scheduled_time, timezone, description, max_rank_diff
        )
        new_id = (await db.fetchrow("SELECT last_insert_rowid()"))[0]
        rec = await db.fetchrow("SELECT * FROM sessions WHERE id=?", new_id)
        view = SessionView(self.bot, rec)
        msg = await interaction.channel.send(embed=session_embed(rec,0,dict(tank=0,dps=0,support=0)),
                                             view=view)
        await db.execute("UPDATE sessions SET message_id=? WHERE id=?", msg.id, new_id)
        await interaction.response.send_message(
            f"Session #{new_id} created!", ephemeral=True)

    # Additional slash commands: /join-queue, /leave-queue, /view-sessions…
    # …

async def setup(bot):
    await bot.add_cog(SessionCog(bot))
