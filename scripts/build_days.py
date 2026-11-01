#!/usr/bin/env python3
"""Build data/days.json: the Graveyard Keeper 2 six-day week (the HUD day wheel).

Run from anywhere (stdlib only):
    python3 -I scripts/build_days.py            # writes data/days.json
    python3 -I scripts/build_days.py --check    # builds + validates, writes nothing
    python3 -I scripts/build_days.py --date 2026-10-30   # pin meta.built

What is derived (deterministically) from data/game-texts/gk2_textos.json:
  * the set of day ids: every <sprite name="day_X"> found in the texts (must be 6);
  * the official en/pt sin names (from the portal fragment names, portal_stone_X);
  * per day, every game text that shows that day's glyph ("mentions");
  * the official quote + pt text attached to each curated event, and the official
    title of the quest that unlocks it;
  * validation: every game-text key cited by a curated event must exist, and the
    primary key of a day-gated event must show that day's glyph.

What is hand-curated (the EVENTS / DAY_ART / ORDER tables below), with provenance:
  * the week order (wikily.gg calendar page + 3 web guides; the game never states it);
  * glyph descriptions and disc colours (measured from the official day_X.png icons);
  * the short en/pt event lines shown in the app.
Game texts are untrusted data: they are only parsed, never executed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXTS = ROOT / "data" / "game-texts" / "gk2_textos.json"
ITEMS = ROOT / "data" / "gk2.json"
OUT = ROOT / "data" / "days.json"

# --------------------------------------------------------------------------------------
# Week order. The game never writes the order; it shows six glyphs on a wheel.
# wikily.gg/graveyard-keeper-2/calendar ("Day of the week: 1 of 6" ... "6 of 6") and
# gamer-guides.com / gamebrief.net give Gluttony, Sloth, Lust, Envy, Pride, Wrath;
# roonby.com and prodigygamers.com give the same cycle but start counting at Wrath.
# --------------------------------------------------------------------------------------
ORDER = ["gluttony", "sloth", "lust", "envy", "pride", "wrath"]
ORDER_CONFIDENCE = "likely"

# pt grammatical gender of the official sin names (for "Dia da/do X")
PT_ARTICLE = {"gluttony": "da", "sloth": "da", "lust": "da", "envy": "da", "pride": "do", "wrath": "da"}

# Glyph + disc colour, measured from the official HUD icons (wikily media: day_<id>.png,
# copied to data/icons/day__<id>.png). Colour = the bright disc field behind the gold glyph.
DAY_ART = {
    "gluttony": {"glyph": "trident / fork-like symbol (ψ), gold on a brown-orange disc",
                 "glyph_pt": "tridente / garfo (ψ), dourado em disco marrom-alaranjado", "color": "#8a3e03"},
    "sloth": {"glyph": "crescent moon, gold on a blue disc",
              "glyph_pt": "lua crescente, dourada em disco azul", "color": "#15619f"},
    "lust": {"glyph": "Venus symbol (♀), gold on a red disc",
             "glyph_pt": "símbolo de Vênus (♀), dourado em disco vermelho", "color": "#ba1010"},
    "envy": {"glyph": "circle with two horns on top, like ♉ (bull's head), gold on a green disc",
             "glyph_pt": "círculo com dois chifres (♉), dourado em disco verde", "color": "#038603"},
    "pride": {"glyph": "radiant sun with eight rays, gold on a purple disc",
              "glyph_pt": "sol com oito raios, dourado em disco roxo", "color": "#732fa6"},
    "wrath": {"glyph": "circle topped by an upward arrow / flame (like ♂), gold on a crimson disc",
              "glyph_pt": "círculo com seta / chama para cima (♂), dourado em disco carmim", "color": "#7f222c"},
}

WIKILY_CAL = "wikily:pages/calendar"
URL_ROONBY = "web:https://roonby.com/2026/10/07/graveyard-keeper-2-days-of-the-week-explained-guide-what-to-do/"
URL_PRODIGY = "web:https://prodigygamers.com/?p=37204"
URL_GAMERGUIDES = "web:https://gamer-guides.com/wiki/graveyard-keeper-2/mechanic/the-six-day-week/"
URL_GAMEBRIEF = "web:https://www.gamebrief.net/blog/graveyard-keeper-2-calendar-workshop-hours-guide-2026"

# NPC names: en from the game, pt = official pt-BR name in the game texts.
WHO = {
    "trademaster": ("Trademaster", "Gerente Comercial"),
    "linda": ("Linda", "Linda"),
    "davy": ("Davy the Dagger", "Orlando, Olha a Faca"),
    "goddess": ("Goddess of Nature", "Deusa"),
    "albert": ("Albert (Plague Doctor)", "Alberto (Médico da Peste)"),
    "nun": ("Agatha (the Nun)", "Agatha (a Freira)"),
    "herbert": ("Herbert", "Norberto"),
}

# --------------------------------------------------------------------------------------
# Curated events. Fields:
#   day, kind, task (True = something the player does or buys that day: the Hoje panel gives it a
#   "feito hoje" tick; False = information, no tick), en, pt (short, phone-sized), short (optional (en, pt)
#   hand-written line title, at most 40 letters: the Hoje panel's one-line text when the title before ": " would be
#   vague or the sentence has no ": "), who (WHO key or None), keys (game-text keys,
#   first = primary, must exist), gated (True = primary key must show the day glyph),
#   extra (other sources: wikily:/web:), confidence, items (ids in data/gk2.json),
#   unlock (game-text key of the quest title, or (en, pt) tuple, or None),
#   detail (optional longer (en, pt)).
# Confidence: high = stated by a game text (often also wikily); medium = only wikily /
# a web guide; low = a single unverified guide.
# --------------------------------------------------------------------------------------
EVENTS = [
    # ---------------- Gluttony ----------------
    dict(day="gluttony", kind="other", task=True, who=None,
         en="PR Machine: load Newspapers and Charged Hypno-devices to raise the zombie limit.",
         pt="Máquina de RP: carregue Jornais e Hipno dispositivos carregados para subir o limite de zumbis.",
         keys=["tut_pr_machine_charge", "pr_machine_available_tomorrow"], gated=True,
         extra=[WIKILY_CAL], confidence="high", items=["newspaper", "charged-hypno-device"],
         unlock="43_astrologer_pr_tower",
         detail=("The only day the machine takes a load: +10 for 1 week (PR Machine I) up to +80 for 5 weeks (PR Machine V).",
                 "Único dia em que a máquina aceita carga: de +10 por 1 semana (Máquina I) a +80 por 5 semanas (Máquina V).")),
    # ---------------- Sloth ----------------
    dict(day="sloth", kind="battle", task=True, who="herbert",
         en="Battle day: most Town battles can only be started today.",
         pt="Dia de batalha: a maioria das batalhas do Povoado só pode ser iniciada hoje.",
         keys=["battle_planer_other_day"], gated=True,
         extra=["wikily:battles", WIKILY_CAL], confidence="high", items=[],
         unlock="15_guards_fightback_win"),
    dict(day="sloth", kind="event", task=False, who=None,
         en="The bell rings in the morning and most zombies withdraw to the town centre.",
         pt="O sino toca de manhã e a maioria dos zumbis recua para o centro do Povoado.",
         short=("Bell rings, zombies pull back", "Sino toca e zumbis recuam"),
         keys=["70_guards_bells_10", "16_foreman_letter_foreman_22_3", "49_pre_A4_fights_4"], gated=True,
         extra=[], confidence="high", items=[], unlock=None),
    dict(day="sloth", kind="battle", task=False, who=None,
         en="Exceptions: the Sewer battles and two story battles can be fought on any day.",
         pt="Exceções: as batalhas dos Esgotos e duas batalhas da história valem em qualquer dia.",
         short=("Battles open on any day", "Batalhas que valem qualquer dia"),
         keys=[], gated=False,
         extra=["wikily:battles", WIKILY_CAL], confidence="medium", items=[], unlock=None,
         detail=("Any day: Break Through to the Port, Sewer Brawl I and II, Break Through to the Bathhouse Basement, "
                 "Sewerena. After Herbert hands over the red banner, battles stay open until the end of the next Sloth.",
                 "Qualquer dia: Break Through to the Port, Sewer Brawl I e II, Break Through to the Bathhouse Basement, "
                 "Sewerena. Depois que o Norberto entrega o estandarte vermelho, as batalhas ficam abertas até o fim da "
                 "próxima Preguiça.")),
    # ---------------- Lust ----------------
    dict(day="lust", kind="merchant", task=True, who="trademaster",
         en="Trade ship at the Main Pier: the Trademaster has new exotic goods.",
         pt="Navio mercante no Cais Principal: o Gerente Comercial tem produtos exóticos novos.",
         keys=["36_port_trademaster_lenses_5", "35_port_pop_new_people_4", "quest_closed_36_port_trademaster_lenses_d"],
         gated=True, extra=[], confidence="high", items=[], unlock="36_port_trademaster_lenses"),
    dict(day="lust", kind="npc", task=True, who="linda",
         en="Linda (Dockside Club) takes Green Scrolls: more citizens and a higher Likes limit.",
         pt="Linda (Clube do Cais) recebe Pergaminhos Verdes: mais moradores e limite maior de curtidas.",
         keys=["tut_town_houses"], gated=True,
         extra=[WIKILY_CAL, "wikily:characters/linda"], confidence="high", items=["green-scroll"],
         unlock="35_port_pop_new_people_1"),
    dict(day="lust", kind="npc", task=True, who="davy",
         en="Davy the Dagger (Dockside Club) takes looter orders, paid in Keys for Looters.",
         pt="Orlando, Olha a Faca (Clube do Cais) aceita encomendas aos saqueadores, pagas com chaves.",
         short=("Davy the Dagger takes looter orders", "Orlando aceita encomendas"),
         keys=["34_port_looters_keys_7"], gated=True,
         extra=["wikily:pages/looter-orders", "wikily:characters/davy-dagger"], confidence="high",
         items=["keys-for-looters"], unlock="34_port_looters_meet"),
    dict(day="lust", kind="quest", task=True, who="trademaster",
         en="High Price: buy the Lust portal fragment from the Trademaster (1 gold).",
         pt="Preço Salgado: compre o fragmento de portal da Luxúria com o Gerente Comercial (1 ouro).",
         keys=["quest_open_125_astrologer_third_buy_d", "125_astrologer_third_10"], gated=True,
         extra=["wikily:quests/high-price"], confidence="high", items=["portal-fragment-lust"],
         unlock="125_astrologer_third_ask"),
    dict(day="lust", kind="quest", task=True, who="linda",
         en="Concept for a Concert: Linda's concert can only start today.",
         pt="Conceito para um Concerto: o show da Linda só pode começar hoje.",
         keys=["67_port_incense_6"], gated=True,
         extra=["wikily:quests/concept-for-a-concert"], confidence="high", items=[],
         unlock="68_port_concert_start"),
    dict(day="lust", kind="other", task=False, who=None,
         en="At the very end of the day the Resurrection Lab gets its power back for Envy.",
         pt="No fim do dia, o Laboratório de Ressurreição recarrega para o dia da Inveja.",
         short=("Resurrection Lab recharges tonight", "Laboratório recarrega à noite"),
         keys=[], gated=False, extra=[WIKILY_CAL], confidence="medium", items=[], unlock=None),
    # ---------------- Envy ----------------
    dict(day="envy", kind="other", task=True, who=None,
         en="Resurrection day: the storm powers the lab; one use raises a zombie on every prepared table.",
         pt="Dia de ressurreição: a tempestade energiza o laboratório; um uso ressuscita um zumbi em cada mesa pronta.",
         keys=["tut_resurrection_day", "tut_resurrection_device", "resurrection_available_tomorrow",
               "resurrection_no_power", "137_base_resurection_room_9", "137_base_resurection_room_11"],
         gated=True, extra=[WIKILY_CAL], confidence="high",
         items=["reanimation-liquid", "bronze-zombie-collar", "steel-zombie-collar", "golden-zombie-collar"],
         unlock=("After repairing the Resurrection device", "Depois de consertar o Dispositivo de Ressurreição"),
         detail=("Each table needs a corpse with all 6 organs, 1 Reanimation Liquid and a good enough collar. "
                 "Once used, the power is gone until the next Envy.",
                 "Cada mesa precisa de um corpo com os 6 órgãos, 1 Líquido de reanimação e uma coleira adequada. "
                 "Depois de usar, só no próximo dia da Inveja.")),
    dict(day="envy", kind="npc", task=True, who="goddess",
         en="Blue Crystals (the Goddess's tears) appear by her statue in the Heart of the Swamp.",
         pt="Cristais azuis (lágrimas da Deusa) surgem junto à estátua no Coração do Pântano.",
         short=("Blue Crystals by the Goddess statue", "Cristais azuis junto à estátua"),
         keys=["quest_closed_63_swamp_goddess_speak_d", "63_swamp_goddess_32_c_3"], gated=True,
         extra=[WIKILY_CAL], confidence="high", items=["blue-crystal"], unlock="62_swamp_fairy_find",
         detail=("A pile of 4; a new pile only comes after the last one is collected. Every zombie collar needs one.",
                 "Uma pilha de 4; outra só aparece depois de pegar a anterior. Toda coleira de zumbi usa um.")),
    dict(day="envy", kind="church", task=False, who=None,
         en="Exception: the Prayer for Storms sermon (God of the storms) allows resurrection on any day.",
         pt="Exceção: o sermão Oração das tempestades (Deus das Tempestades) libera ressurreição em qualquer dia.",
         short=("Prayer for Storms sermon", "Sermão Oração das tempestades"),
         keys=["buff_storm_d", "buff_storm", "prayer_storms"], gated=False,
         extra=["wikily:sermons/prayer-for-storms"], confidence="high", items=[], unlock=None,
         detail=("The buff lasts 1 h 30 min of game time (wikily).", "O efeito dura 1 h 30 min de jogo (wikily).")),
    dict(day="envy", kind="npc", task=True, who="albert",
         en="Albert, the Plague Doctor, may give 2 free zombies to resurrect (unconfirmed).",
         pt="Alberto, o Médico da Peste, pode dar 2 zumbis grátis para ressuscitar (não confirmado).",
         short=("Albert may give 2 free zombies", "Alberto pode dar 2 zumbis"),
         keys=[], gated=False, extra=[URL_ROONBY, URL_PRODIGY], confidence="low", items=[], unlock=None),
    # ---------------- Pride ----------------
    dict(day="pride", kind="other", task=True, who=None,
         en="Town orders can only be accepted today, at the order board.",
         pt="Pedidos do povoado só podem ser aceitos hoje, no quadro de pedidos.",
         short=("Town orders, today only", "Pedidos do povoado, só hoje"),
         keys=["tut_commerce_day", "ui_order_possible_days", "tut_commerce_urgent"], gated=True,
         extra=[WIKILY_CAL], confidence="high", items=[], unlock="58_port_supplies_order",
         detail=("Urgent orders must be completed in full within one week; others can be delivered on any day.",
                 "Pedidos urgentes precisam ser concluídos em até uma semana; os demais podem ser entregues em qualquer dia.")),
    dict(day="pride", kind="merchant", task=False, who=None,
         en="Every trader's weekly Likes limit resets.",
         pt="O limite semanal de curtidas de cada comerciante é reiniciado.",
         short=("Traders' Likes limits reset", "Limite de curtidas reinicia"),
         keys=["tt_trade_hap_likes"], gated=True, extra=[WIKILY_CAL], confidence="high", items=[], unlock=None),
    dict(day="pride", kind="other", task=False, who=None,
         en="Town Warehouse payout: crate goods fill your orders, the rest is sold; collect the money at the board.",
         pt="Pagamento do Armazém do Povoado: as caixas abastecem os pedidos, o resto é vendido; o dinheiro fica no quadro.",
         keys=[], gated=False, extra=[WIKILY_CAL], confidence="medium", items=[], unlock=None,
         detail=("Repeatable orders finished since the last Pride can be accepted again.",
                 "Pedidos repetíveis concluídos desde o último Orgulho podem ser aceitos de novo.")),
    # ---------------- Wrath ----------------
    dict(day="wrath", kind="church", task=True, who=None,
         en="Mass day: hold one sermon at the Church.",
         pt="Dia de missa: faça um sermão na Igreja.",
         keys=["tut_sermons_day", "prayer_available_tomorrow", "43_astrologer_pr_tower_2",
               "quest_closed_19_base_ceremony_sermon_d"], gated=True,
         extra=[WIKILY_CAL, "wikily:pages/church-and-sermons"], confidence="high", items=[],
         unlock="17_village_nun_tavern",
         detail=("Only the very first sermon (Holy Moly!) can be held on another day.",
                 "Só o primeiro sermão (Çasinhora!) pode ser feito em outro dia.")),
    dict(day="wrath", kind="npc", task=True, who="nun",
         en="Agatha (Crossroads): set the weekly corpse delivery (none, a few or lots).",
         pt="Agatha (Encruzilhada): defina a entrega semanal de corpos (nenhum, poucos ou muitos).",
         keys=["51_crossroad_fixed_delivery_6", "51_crossroad_fixed_delivery_7"], gated=True,
         extra=[WIKILY_CAL], confidence="high", items=[], unlock="51_crossroad_fixed_delivery_1"),
    dict(day="wrath", kind="npc", task=False, who="nun",
         en="Early story: the Nun comes by to check on the church repairs.",
         pt="Início da história: a Freira passa para ver a reforma da igreja.",
         short=("The Nun visits the church", "A Freira visita a igreja"),
         keys=["17_village_nun_meeting_14"], gated=True, extra=[], confidence="high", items=[],
         unlock="17_village_nun_tavern"),
    dict(day="wrath", kind="quest", task=False, who="nun",
         en="The Nun with the Hairy Ass: Agatha hands over a couple of poor corpses on this day.",
         pt="A Freira do Burro Peludo: Agatha entrega alguns corpos pobres neste dia.",
         keys=["42_crossroad_nun_donkey_12_a_11", "42_crossroad_nun_donkey_12_a_10"], gated=True,
         extra=[], confidence="medium", items=[], unlock="42_crossroad_nun_donkey"),
    dict(day="wrath", kind="other", task=False, who=None,
         en="End of day: a running PR Machine program counts down one week.",
         pt="Fim do dia: o programa ativo da Máquina de RP desconta uma semana.",
         short=("PR Machine: −1 week", "Máquina de RP: −1 semana"),
         keys=[], gated=False, extra=[WIKILY_CAL], confidence="medium", items=[], unlock=None),
]

KINDS = {"npc", "merchant", "church", "battle", "quest", "event", "other"}
CONF = {"high", "medium", "low"}

# Sprites that appear next to day glyphs, rendered as words in quotes.
SPRITE_WORDS = {
    "happiness": ("Likes", "curtidas"),
    "reputation-citizens": ("citizen reputation", "reputação dos cidadãos"),
    "village_REP": ("village reputation", "reputação da vila"),
    "panic": ("panic", "pânico"),
    "brz-m": ("coins", "moedas"), "slv-m": ("", ""), "gld-m": ("", ""),
    "icon_time": ("(urgent)", "(urgente)"),
}

SPRITE_RE = re.compile(r'<sprite name="?([^">]+)"?\s*>')


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def sin_names(texts: dict, day: str) -> dict:
    """Official sin name from the portal fragment text: 'Portal fragment Sloth' / 'Fragmento de Portal: Preguiça'."""
    v = texts[f"portal_stone_{day}"]
    en = re.sub(r"^Portal fragment\s+", "", v["en"]).strip()
    pt = re.sub(r"^Fragmento de Portal:\s*", "", v["pt"]).strip()
    return {"en": en, "pt": pt}


def render(text: str, lang: str, sins: dict) -> str:
    def sub(m):
        name = m.group(1)
        if name.startswith("day_") and name[4:] in sins:
            return sins[name[4:]][lang]
        w = SPRITE_WORDS.get(name)
        return (w[0] if lang == "en" else w[1]) if w else ""
    out = SPRITE_RE.sub(sub, text)
    return re.sub(r"\s+", " ", out).strip()


def build(built: str) -> dict:
    texts = load_json(TEXTS)
    item_ids = set(load_json(ITEMS).get("items", {})) if ITEMS.exists() else set()

    # ---- day ids from the glyph sprites --------------------------------------------
    found = {}
    for k, v in texts.items():
        for lang in ("en", "pt"):
            for name in SPRITE_RE.findall(v.get(lang, "")):
                if name.startswith("day_"):
                    found.setdefault(name[4:], set()).add(k)
    if set(found) != set(ORDER):
        raise SystemExit(f"day sprites in texts {sorted(found)} != ORDER {ORDER}")
    sins = {d: sin_names(texts, d) for d in ORDER + ["greed"]}

    def quote(key):
        v = texts[key]
        return {"key": key, "en": render(v["en"], "en", sins), "pt": render(v["pt"], "pt", sins)}

    # ---- events --------------------------------------------------------------------
    by_day = {d: [] for d in ORDER}
    errors = []
    for i, e in enumerate(EVENTS):
        d = e["day"]
        tag = f"event #{i} ({d}: {e['en'][:40]})"
        if d not in by_day:
            errors.append(f"{tag}: unknown day")
            continue
        if e["kind"] not in KINDS or e["confidence"] not in CONF:
            errors.append(f"{tag}: bad kind/confidence")
        if e.get("short") and max(len(e["short"][0]), len(e["short"][1])) > 40:
            errors.append(f"{tag}: short title over 40 letters")
        if not isinstance(e.get("task"), bool):
            errors.append(f"{tag}: task must be True or False")
        for k in e["keys"]:
            if k not in texts:
                errors.append(f"{tag}: missing game-text key {k}")
        if e["keys"] and e["gated"]:
            primary = texts.get(e["keys"][0], {})
            if f'day_{d}' not in primary.get("en", "") + primary.get("pt", ""):
                errors.append(f"{tag}: primary key {e['keys'][0]} does not show day_{d}")
        for it in e["items"]:
            if item_ids and it not in item_ids:
                errors.append(f"{tag}: unknown item id {it}")
        sources = [f"game-text:{k}" for k in e["keys"]] + list(e["extra"])
        if not sources:
            errors.append(f"{tag}: no source")
        who = WHO[e["who"]] if e["who"] else None
        unlock = None
        if isinstance(e["unlock"], str):
            if e["unlock"] not in texts:
                errors.append(f"{tag}: missing unlock key {e['unlock']}")
            else:
                u = texts[e["unlock"]]
                unlock = {"key": e["unlock"], "en": u["en"].strip(), "pt": u["pt"].strip(), "tr": "official"}
        elif e["unlock"]:
            unlock = {"key": None, "en": e["unlock"][0], "pt": e["unlock"][1], "tr": "machine"}
        ev = {
            "kind": e["kind"],
            "task": bool(e["task"]),
            "en": e["en"],
            "pt": e["pt"],
            "tr": "machine",
            "who": who[0] if who else None,
            "who_pt": who[1] if who else None,
            "source": sources[0] if sources else None,
            "also": sources[1:],
            "confidence": e["confidence"],
            "items": list(e["items"]),
            "unlock": unlock,
            "short": {"en": e["short"][0], "pt": e["short"][1]} if e.get("short") else None,
            "detail": {"en": e["detail"][0], "pt": e["detail"][1]} if e.get("detail") else None,
            "quote": quote(e["keys"][0]) if e["keys"] else None,
        }
        by_day[d].append(ev)
    if errors:
        raise SystemExit("validation failed:\n  " + "\n  ".join(errors))

    # ---- days ----------------------------------------------------------------------
    days = []
    for n, d in enumerate(ORDER):
        s = sins[d]
        art = DAY_ART[d]
        mentions = [quote(k) for k in texts if k in found[d]]  # file order = deterministic
        days.append({
            "id": d,
            "order": n,
            "sin": {"en": s["en"], "pt": s["pt"]},
            "sin_tr": "official",
            "name": {"en": f"Day of {s['en']}", "pt": f"Dia {PT_ARTICLE[d]} {s['pt']}"},
            "tr": "likely",
            "sprite": f"day_{d}",
            "glyph": art["glyph"],
            "glyph_pt": art["glyph_pt"],
            "color": art["color"],
            "prev": ORDER[(n - 1) % 6],
            "next": ORDER[(n + 1) % 6],
            "events": by_day[d],
            "mentions": mentions,
        })

    meta = {
        "schema": 1,
        "week_length": len(ORDER),
        "order": ORDER,
        "order_confidence": ORDER_CONFIDENCE,
        "order_note": {
            "en": "The game never writes the order. wikily.gg numbers the days Gluttony=1 ... Wrath=6, and four web "
                  "guides agree on the same cycle (two of them start counting at Wrath). Which weekday a new game "
                  "starts on, and how the game's day counter maps to a weekday, are unknown.",
            "pt": "O jogo nunca escreve a ordem. O wikily.gg numera Gula=1 ... Ira=6, e quatro guias da web concordam "
                  "com o mesmo ciclo (dois começam a contar pela Ira). Não se sabe em que dia um jogo novo começa "
                  "nem como o contador de dias do jogo se converte em dia da semana.",
        },
        "wheel": {
            "direction": "clockwise",
            "direction_confidence": "medium",
            "current_marker": "the current day's medallion sticks out of the ring (arrow)",
            "highlight": "today's and tomorrow's glyphs are lit",
            "centre_picture": "each day's own picture in the centre unlocks with a story step",
            "source": URL_GAMERGUIDES[4:] + " ; wikily:pages/calendar",
        },
        "greed": {
            "sin": sins["greed"],
            "note": {"en": "Greed is the 7th sin and portal fragment but has no day: \"six looks better on the wheel of time\".",
                     "pt": "A Ganância é o 7º pecado e fragmento de portal, mas não tem dia: \"seis fica melhor na roda do tempo\"."},
            "source": "game-text:113_sewers_god_34 ; game-text:113_sewers_god_35",
        },
        "lore_note": {
            "en": "In the story the Astrologer complains that the days of the week are 'a total mess' and 'changing "
                  "places'; no source reports the order actually changing during play.",
            "pt": "Na história, o Astrólogo reclama que os dias da semana estão 'bagunçados' e 'trocando de lugar'; "
                  "nenhuma fonte relata a ordem mudando de fato durante o jogo.",
            "source": "game-text:108_astrologer_pieces_10 ; game-text:158_astrologer_palace_help_6",
        },
        "sources": [
            "game-text: data/game-texts/gk2_textos.json (game 1.011, lng_en + lng_pt-br)",
            "wikily:pages/calendar = https://wikily.gg/api/wikis/graveyard-keeper-2/pages/calendar (rev 2026-09-30)",
            "wikily:<dataset>/<key> = https://wikily.gg/api/wikis/graveyard-keeper-2/datasets/<dataset>/list",
            URL_GAMERGUIDES, URL_GAMEBRIEF, URL_ROONBY, URL_PRODIGY,
            "icons: media.wikily.gg day_<id>.png (official game sprites), copied to data/icons/day__<id>.png",
        ],
        "credits": "Day data partly from the Graveyard Keeper 2 Wiki by Wikily (https://wikily.gg/graveyard-keeper-2), "
                   "© NX Software. Game content © Lazy Bear Games / tinyBuild.",
        "legend": {
            "tr": "official = verbatim game text; likely = built from official words (e.g. 'Dia da' + official sin); "
                  "machine = written for this app (not from the game)",
            "confidence": "high = a game text says it; medium = only wikily / a web guide; low = one unverified guide",
            "source": "first source; 'also' lists the rest. game-text:<key> | wikily:<dataset or page>/<key> | web:<url>",
        },
        "built": built,
        "notes": {
            "pt": "A semana tem 6 dias, cada um com o símbolo de um pecado (a Ganância fica de fora). O jogo não "
                  "escreve os nomes: a roda no canto da tela mostra só os símbolos, e o dia atual fica destacado.",
            "en": "The week has 6 days, each shown by a sin's glyph (Greed has no day). The game never writes the "
                  "names: the wheel in the screen corner only shows the glyphs, with the current day marked.",
        },
    }
    return {"meta": meta, "days": days}


def validate(doc: dict) -> None:
    days = doc["days"]
    assert doc["meta"]["week_length"] == 6 == len(days)
    assert [d["order"] for d in days] == list(range(6))
    assert len({d["id"] for d in days}) == 6
    for d in days:
        assert re.fullmatch(r"#[0-9a-f]{6}", d["color"])
        assert d["events"], d["id"]
        for e in d["events"]:
            for f in ("kind", "en", "pt", "tr", "who", "source", "confidence", "items"):
                assert f in e, (d["id"], f)
            assert e["kind"] in KINDS and e["confidence"] in CONF
            assert e["source"].split(":", 1)[0] in ("game-text", "wikily", "web")
    json.loads(json.dumps(doc, ensure_ascii=False))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="build and validate only")
    ap.add_argument("--date", help="value for meta.built (default: today, but data/days.json keeps its date when "
                                   "nothing else changed)")
    args = ap.parse_args(argv)
    doc = build(args.date or _dt.date.today().isoformat())
    if not args.date:   # same week as on disk: keep its meta.built (it goes into the page; a rerun writes nothing)
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            if dict(old, meta=dict(old["meta"], built=doc["meta"]["built"])) == doc:
                doc = old
        except (OSError, ValueError, KeyError, TypeError):
            pass
    validate(doc)
    n_ev = sum(len(d["events"]) for d in doc["days"])
    n_m = sum(len(d["mentions"]) for d in doc["days"])
    if args.check:
        print(f"ok: 6 days, {n_ev} events, {n_m} mentions (nothing written)")
        return 0
    text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
        print(f"{OUT.relative_to(ROOT)} up to date: 6 days, {n_ev} events, {n_m} mentions (nothing written)")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: 6 days, {n_ev} events, {n_m} mentions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
