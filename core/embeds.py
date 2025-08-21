import discord, json
from core import models, timeutil

def session_embed(rec: dict, queue_size: int, fills: dict[str,int]):
    """Return a discord.Embed reflecting live state."""
    start = timeutil.utc_to_local(rec['scheduled_time'], rec['timezone'])
    em = discord.Embed(
        title=f"Overwatch {rec['game_mode']} – #{rec['id']}",
        description=rec.get("description") or "No description.",
        color=discord.Color.blue()
    )
    em.add_field(
        name="⏰ Time",
        value=f"<t:{int(start.timestamp())}:F> ({rec['timezone']})",
        inline=False
    )
    em.add_field(name="Status", value=rec['status'])
    em.add_field(name="Queue", value=f"{queue_size} waiting")
    em.add_field(
        name="Slots",
        value="\n".join(f"{role}: {fills[role]}/{need}" 
                        for role,need in models.GAME_MODES[rec['game_mode']].items() 
                        if need),
        inline=False
    )
    em.set_footer(text="Use buttons or /join-queue to enter.")
    return em
