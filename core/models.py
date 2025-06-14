from enum import StrEnum, IntEnum

class Rank(StrEnum):
    bronze="Bronze🟫"
    silver="Silver⚪"
    gold="Gold🟨"
    platinum="Platinum🟦"
    diamond="Diamond💎"
    master="Master🟧"
    grandmaster="Grandmaster🔺"
    champion="Champion👑"

class Division(IntEnum):
    five=5
    four=4
    three=3
    two=2
    one=1

ROLE_EMOJIS = {"tank":"🛡️","dps":"⚔️","support":"💉"}
GAME_MODES = {"5v5":{"tank":1,"dps":2,"support":2}, "6v6":{"tank":0,"dps":6,"support":0}, "Stadium":{"tank":0,"dps":6,"support":0}}