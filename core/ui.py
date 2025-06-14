import discord
from discord import Interaction

class SessionView(discord.ui.View):
    def __init__(self, bot, session_record):
        super().__init__(timeout=None)
        self.bot = bot
        self.session = session_record