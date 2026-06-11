import random

MAJOR_ARCANA = [
    {"name": "The Fool", "number": 0, "meaning": "New beginnings, innocence, spontaneity, free spirit"},
    {"name": "The Magician", "number": 1, "meaning": "Willpower, desire, resourcefulness, skill"},
    {"name": "The High Priestess", "number": 2, "meaning": "Intuition, mystery, subconscious mind"},
    {"name": "The Empress", "number": 3, "meaning": "Femininity, beauty, nature, abundance"},
    {"name": "The Emperor", "number": 4, "meaning": "Authority, structure, stability, control"},
    {"name": "The Hierophant", "number": 5, "meaning": "Tradition, conformity, spiritual wisdom"},
    {"name": "The Lovers", "number": 6, "meaning": "Love, harmony, relationships, choices"},
    {"name": "The Chariot", "number": 7, "meaning": "Willpower, determination, victory, assertion"},
    {"name": "Strength", "number": 8, "meaning": "Courage, inner strength, compassion"},
    {"name": "The Hermit", "number": 9, "meaning": "Soul-searching, introspection, solitude"},
    {"name": "Wheel of Fortune", "number": 10, "meaning": "Change, cycles, fate, destiny"},
    {"name": "Justice", "number": 11, "meaning": "Fairness, truth, cause and effect, law"},
    {"name": "The Hanged Man", "number": 12, "meaning": "Surrender, new perspective, pause"},
    {"name": "Death", "number": 13, "meaning": "Transformation, endings, change"},
    {"name": "Temperance", "number": 14, "meaning": "Balance, moderation, patience"},
    {"name": "The Devil", "number": 15, "meaning": "Bondage, materialism, shadow self"},
    {"name": "The Tower", "number": 16, "meaning": "Sudden upheaval, revelation, chaos"},
    {"name": "The Star", "number": 17, "meaning": "Hope, faith, inspiration, serenity"},
    {"name": "The Moon", "number": 18, "meaning": "Illusion, fear, anxiety, subconscious"},
    {"name": "The Sun", "number": 19, "meaning": "Joy, success, vitality, positivity"},
    {"name": "Judgement", "number": 20, "meaning": "Rebirth, inner calling, absolution"},
    {"name": "The World", "number": 21, "meaning": "Completion, accomplishment, fulfillment"},
]

SUITS = ["Wands", "Cups", "Swords", "Pentacles"]
SUIT_MEANINGS = {
    "Wands": "Creativity, action, passion, career",
    "Cups": "Emotions, relationships, love, intuition",
    "Swords": "Intellect, conflict, truth, mental clarity",
    "Pentacles": "Material world, work, health, finances",
}
COURT_RANKS = {"Page": "Youth, exploration, message", "Knight": "Action, pursuit, adventure", "Queen": "Nurturing, grace, inner power", "King": "Authority, leadership, mastery"}
PIP_MEANINGS = {
    1: "New beginnings, potential, opportunity",
    2: "Balance, partnership, decisions",
    3: "Growth, expansion, teamwork",
    4: "Stability, foundation, consolidation",
    5: "Conflict, struggle, loss",
    6: "Harmony, success, cooperation",
    7: "Challenge, perseverance, competition",
    8: "Movement, progress, action",
    9: "Fulfillment, wisdom, reflection",
    10: "Completion, culmination, endings",
}


def _build_deck():
    deck = []
    for arcana in MAJOR_ARCANA:
        deck.append({**arcana, "type": "major", "suit": None, "rank": None})
    for suit in SUITS:
        for rank_num in range(1, 11):
            deck.append({
                "name": f"{rank_num} of {suit}",
                "number": None,
                "meaning": PIP_MEANINGS[rank_num],
                "type": "minor",
                "suit": suit,
                "rank": str(rank_num),
            })
        for rank_name, rank_meaning in COURT_RANKS.items():
            deck.append({
                "name": f"{rank_name} of {suit}",
                "number": None,
                "meaning": rank_meaning,
                "type": "court",
                "suit": suit,
                "rank": rank_name,
            })
    return deck


_DECK = _build_deck()

SPREADS = {
    "single": {"positions": ["Your Card"], "count": 1},
    "three": {"positions": ["Past", "Present", "Future"], "count": 3},
    "cross": {"positions": ["Situation", "Challenge", "Past", "Future", "Outcome"], "count": 5},
}


def draw_cards(spread: str = "three") -> dict:
    if spread not in SPREADS:
        spread = "three"
    info = SPREADS[spread]
    cards = random.sample(_DECK, info["count"])
    result = {"spread": spread, "cards": []}
    for i, card in enumerate(cards):
        pos = info["positions"][i] if i < len(info["positions"]) else f"Position {i+1}"
        upright = random.random() > 0.25
        result["cards"].append({
            "position": pos,
            "name": card["name"],
            "upright": upright,
            "orientation": "upright" if upright else "reversed",
            "type": card["type"],
            "suit": card["suit"],
            "meaning": card["meaning"],
        })
    return result
