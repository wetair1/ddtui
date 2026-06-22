#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddtui - a tiny ASCII / curses dashboard for DDraceNetwork (DDNet).

Tools, picked from an interactive menu (like `iuse`):

  * STATS    - look up a player: points, global / team ranks, points by map
               type, recent finishes, favorite server. (ddnet.org json2 API)
  * SERVERS  - live server browser: search online servers, map, gametype,
               ping region and the players currently online.
  * OVERVIEW - master-server overview: total players online, by region,
               by gametype and the most populated maps right now.
  * FIND     - find which online servers a given player name is on right now.
  * COMPARE  - compare two players side by side (points & ranks).
  * MAP      - map info: type, difficulty, mapper, finishes, median time
               and the current top ranks. (ddnet.org maps json API)

Pure Python 3 standard library, zero dependencies. RU/EN auto-localized.

Usage:
    python3 ddtui.py                  # interactive GUI (menu)
    python3 ddtui.py nameless tee      # direct player lookup
    python3 ddtui.py --servers         # dump the server list
    python3 ddtui.py --overview        # master-server overview
    python3 ddtui.py --find nameless   # where is this player online
    python3 ddtui.py -c nameless cor   # compare two players
    python3 ddtui.py --map Kobra       # map info
    python3 ddtui.py -p "Cor" --json   # raw JSON for scripting

MIT License.
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

__version__ = "0.2.0"

PLAYER_API = "https://ddnet.org/players/?json2="
SERVERS_API = "https://master1.ddnet.org/ddnet/15/servers.json"
MAPS_API = "https://ddnet.org/maps/?json="
USER_AGENT = "ddtui/%s (+https://github.com/wetair1)" % __version__


# --------------------------------------------------------------------------- #
# Localization                                                                #
# --------------------------------------------------------------------------- #

def detect_lang():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(var, "")
        if v:
            low = v.lower()
            if low.startswith("ru") or low.startswith("uk"):
                return "ru"
            return "en"
    return "en"


LANG = detect_lang()

STR = {
    "ru": {
        "mode_title": "ddtui \u2014 \u0447\u0442\u043e \u0441\u043c\u043e\u0442\u0440\u0438\u043c?",
        "mode_hint": " \u2191\u2193 \u00b7 Enter \u2014 \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u00b7 Esc \u2014 \u0432\u044b\u0445\u043e\u0434",
        "mode_stats": "\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430 \u0438\u0433\u0440\u043e\u043a\u0430",
        "mode_servers": "\u0411\u0440\u0430\u0443\u0437\u0435\u0440 \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432 (\u043e\u043d\u043b\u0430\u0439\u043d)",
        "mode_overview": "\u041e\u0431\u0437\u043e\u0440 \u043c\u0430\u0441\u0442\u0435\u0440-\u0441\u0435\u0440\u0432\u0435\u0440\u0430",
        "mode_find": "\u041d\u0430\u0439\u0442\u0438 \u0438\u0433\u0440\u043e\u043a\u0430 \u043e\u043d\u043b\u0430\u0439\u043d",
        "mode_compare": "\u0421\u0440\u0430\u0432\u043d\u0438\u0442\u044c \u0434\u0432\u0443\u0445 \u0438\u0433\u0440\u043e\u043a\u043e\u0432",
        "mode_map": "\u0418\u043d\u0444\u043e \u043e \u043a\u0430\u0440\u0442\u0435",
        "prompt_player": " \u0418\u043c\u044f \u0438\u0433\u0440\u043e\u043a\u0430 (\u0442\u043e\u0447\u043d\u043e, \u043a\u0430\u043a \u0432 \u0438\u0433\u0440\u0435):",
        "prompt_find": " \u0418\u043c\u044f \u0438\u0433\u0440\u043e\u043a\u0430 \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430 \u043e\u043d\u043b\u0430\u0439\u043d:",
        "prompt_map": " \u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043a\u0430\u0440\u0442\u044b:",
        "prompt_cmp1": " \u041f\u0435\u0440\u0432\u044b\u0439 \u0438\u0433\u0440\u043e\u043a:",
        "prompt_cmp2": " \u0412\u0442\u043e\u0440\u043e\u0439 \u0438\u0433\u0440\u043e\u043a:",
        "prompt_keys": " Enter \u2014 \u0438\u0441\u043a\u0430\u0442\u044c \u00b7 Esc \u2014 \u043d\u0430\u0437\u0430\u0434",
        "loading": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430\u2026",
        "net_error": "\u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u0435\u0442\u0438: %s",
        "not_found": "\u0418\u0433\u0440\u043e\u043a \u00ab%s\u00bb \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.",
        "map_not_found": "\u041a\u0430\u0440\u0442\u0430 \u00ab%s\u00bb \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u0430.",
        "no_servers": "\u0421\u0435\u0440\u0432\u0435\u0440\u044b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b.",
        "find_none": "\u0418\u0433\u0440\u043e\u043a \u00ab%s\u00bb \u0441\u0435\u0439\u0447\u0430\u0441 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u043d\u0438 \u043d\u0430 \u043e\u0434\u043d\u043e\u043c \u0441\u0435\u0440\u0432\u0435\u0440\u0435.",
        "srv_pick_title": " ddtui \u2014 \u0441\u0435\u0440\u0432\u0435\u0440\u044b: \u0432\u044b\u0431\u0435\u0440\u0438 (Enter \u2014 \u0434\u0435\u0442\u0430\u043b\u0438)",
        "srv_pick_hint": " \u041f\u0435\u0447\u0430\u0442\u0430\u0439 \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430 \u00b7 \u2191\u2193 \u00b7 Enter \u2014 \u0434\u0435\u0442\u0430\u043b\u0438 \u00b7 Esc \u2014 \u043d\u0430\u0437\u0430\u0434",
        "srv_none_match": " \u041d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e. \u0418\u0437\u043c\u0435\u043d\u0438 \u0437\u0430\u043f\u0440\u043e\u0441 \u0438\u043b\u0438 Backspace.",
        "scroll_hint": " \u2191\u2193/PgUp/PgDn \u2014 \u043b\u0438\u0441\u0442\u0430\u0442\u044c \u00b7 Esc \u2014 \u043d\u0430\u0437\u0430\u0434",
        "players_online": "\u0438\u0433\u0440\u043e\u043a\u043e\u0432 \u043e\u043d\u043b\u0430\u0439\u043d",
        "cancelled": "\u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e.",
        "l_points": "\u043e\u0447\u043a\u0438",
        "l_global": "\u043c\u0438\u0440\u043e\u0432\u043e\u0439 \u0440\u0430\u043d\u0433",
        "l_team": "\u043a\u043e\u043c\u0430\u043d\u0434\u043d\u044b\u0439 \u0440\u0430\u043d\u0433",
        "l_year": "\u0437\u0430 \u0433\u043e\u0434",
        "l_month": "\u0437\u0430 \u043c\u0435\u0441\u044f\u0446",
        "l_week": "\u0437\u0430 \u043d\u0435\u0434\u0435\u043b\u044e",
        "l_fav": "\u043b\u044e\u0431\u0438\u043c\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440",
        "l_first": "\u043f\u0435\u0440\u0432\u044b\u0439 \u0444\u0438\u043d\u0438\u0448",
        "l_hours": "\u0447\u0430\u0441\u043e\u0432 \u0437\u0430 \u0433\u043e\u0434",
        "l_bytype": "\u043e\u0447\u043a\u0438 \u043f\u043e \u0442\u0438\u043f\u0430\u043c \u043a\u0430\u0440\u0442",
        "l_last": "\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u0444\u0438\u043d\u0438\u0448\u0438",
        "l_map": "\u043a\u0430\u0440\u0442\u0430",
        "l_gametype": "\u0440\u0435\u0436\u0438\u043c",
        "l_region": "\u0440\u0435\u0433\u0438\u043e\u043d",
        "l_version": "\u0432\u0435\u0440\u0441\u0438\u044f",
        "l_players": "\u0438\u0433\u0440\u043e\u043a\u0438",
        "l_type": "\u0442\u0438\u043f",
        "l_difficulty": "\u0441\u043b\u043e\u0436\u043d\u043e\u0441\u0442\u044c",
        "l_mapper": "\u043c\u0430\u043f\u043f\u0435\u0440",
        "l_release": "\u0440\u0435\u043b\u0438\u0437",
        "l_finishes": "\u0444\u0438\u043d\u0438\u0448\u0435\u0439",
        "l_finishers": "\u0444\u0438\u043d\u0438\u0448\u0435\u0440\u043e\u0432",
        "l_median": "\u043c\u0435\u0434\u0438\u0430\u043d\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f",
        "l_toprank": "\u0442\u043e\u043f \u0440\u0430\u043d\u0433\u0438",
        "l_byregion": "\u0438\u0433\u0440\u043e\u043a\u0438 \u043f\u043e \u0440\u0435\u0433\u0438\u043e\u043d\u0430\u043c",
        "l_bygametype": "\u0438\u0433\u0440\u043e\u043a\u0438 \u043f\u043e \u0440\u0435\u0436\u0438\u043c\u0430\u043c",
        "l_topmaps": "\u0441\u0430\u043c\u044b\u0435 \u043f\u043e\u043f\u0443\u043b\u044f\u0440\u043d\u044b\u0435 \u043a\u0430\u0440\u0442\u044b",
        "l_totalservers": "\u0432\u0441\u0435\u0433\u043e \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432",
        "l_occupied": "\u0441 \u0438\u0433\u0440\u043e\u043a\u0430\u043c\u0438",
        "unranked": "\u0431\u0435\u0437 \u0440\u0430\u043d\u0433\u0430",
        "h_player": "\u0438\u043c\u044f \u0438\u0433\u0440\u043e\u043a\u0430 \u0434\u043b\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0438",
        "h_p": "\u0438\u043c\u044f \u0438\u0433\u0440\u043e\u043a\u0430 (\u043c\u043e\u0436\u043d\u043e \u0441 \u043f\u0440\u043e\u0431\u0435\u043b\u0430\u043c\u0438)",
        "h_servers": "\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432 \u0438 \u0432\u044b\u0439\u0442\u0438",
        "h_overview": "\u043e\u0431\u0437\u043e\u0440 \u043c\u0430\u0441\u0442\u0435\u0440-\u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u0438 \u0432\u044b\u0439\u0442\u0438",
        "h_find": "\u043d\u0430\u0439\u0442\u0438, \u043d\u0430 \u043a\u0430\u043a\u0438\u0445 \u0441\u0435\u0440\u0432\u0435\u0440\u0430\u0445 \u0438\u0433\u0440\u043e\u043a \u043e\u043d\u043b\u0430\u0439\u043d",
        "h_compare": "\u0441\u0440\u0430\u0432\u043d\u0438\u0442\u044c \u0434\u0432\u0443\u0445 \u0438\u0433\u0440\u043e\u043a\u043e\u0432",
        "h_map": "\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0438\u043d\u0444\u043e \u043e \u043a\u0430\u0440\u0442\u0435",
        "h_theme": "\u0446\u0432\u0435\u0442\u043e\u0432\u0430\u044f \u0442\u0435\u043c\u0430",
        "h_filter": "\u0444\u0438\u043b\u044c\u0442\u0440 \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432 \u043f\u043e \u043f\u043e\u0434\u0441\u0442\u0440\u043e\u043a\u0435",
        "h_limit": "\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u0432 \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c (\u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e 40)",
        "h_json": "\u0432\u044b\u0432\u0435\u0441\u0442\u0438 \u0441\u044b\u0440\u043e\u0439 JSON",
        "h_nocolor": "\u043e\u0442\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0446\u0432\u0435\u0442",
        "h_listthemes": "\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0442\u0435\u043c\u044b \u0438 \u0432\u044b\u0439\u0442\u0438",
        "desc": "ddtui \u2014 ASCII-\u0434\u0430\u0448\u0431\u043e\u0440\u0434 DDNet: \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430, \u0441\u0435\u0440\u0432\u0435\u0440\u044b, \u043e\u0431\u0437\u043e\u0440, \u043f\u043e\u0438\u0441\u043a, \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u0435 \u0438 \u043a\u0430\u0440\u0442\u044b.",
        "epilog": "\u0411\u0435\u0437 \u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442\u043e\u0432 \u043e\u0442\u043a\u0440\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u0438\u043d\u0442\u0435\u0440\u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e.",
        "curses_required": "\u041d\u0443\u0436\u0435\u043d \u043c\u043e\u0434\u0443\u043b\u044c curses (\u0438\u043b\u0438 \u0437\u0430\u043f\u0443\u0441\u0442\u0438 \u0441 \u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442\u043e\u043c, \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: ddtui.py nameless)",
    },
    "en": {
        "mode_title": "ddtui \u2014 what do you want?",
        "mode_hint": " \u2191\u2193 \u00b7 Enter \u2014 select \u00b7 Esc \u2014 quit",
        "mode_stats": "Player stats",
        "mode_servers": "Server browser (online)",
        "mode_overview": "Master-server overview",
        "mode_find": "Find player online",
        "mode_compare": "Compare two players",
        "mode_map": "Map info",
        "prompt_player": " Player name (exact, as in game):",
        "prompt_find": " Player name to find online:",
        "prompt_map": " Map name:",
        "prompt_cmp1": " First player:",
        "prompt_cmp2": " Second player:",
        "prompt_keys": " Enter \u2014 search \u00b7 Esc \u2014 back",
        "loading": "Loading\u2026",
        "net_error": "Network error: %s",
        "not_found": "Player \u00ab%s\u00bb not found.",
        "map_not_found": "Map \u00ab%s\u00bb not found.",
        "no_servers": "No servers found.",
        "find_none": "Player \u00ab%s\u00bb is not on any server right now.",
        "srv_pick_title": " ddtui \u2014 servers: pick one (Enter \u2014 details)",
        "srv_pick_hint": " Type to search \u00b7 \u2191\u2193 \u00b7 Enter \u2014 details \u00b7 Esc \u2014 back",
        "srv_none_match": " Nothing found. Change the query or Backspace.",
        "scroll_hint": " \u2191\u2193/PgUp/PgDn \u2014 scroll \u00b7 Esc \u2014 back",
        "players_online": "players online",
        "cancelled": "Cancelled.",
        "l_points": "points",
        "l_global": "global rank",
        "l_team": "team rank",
        "l_year": "past year",
        "l_month": "past month",
        "l_week": "past week",
        "l_fav": "favorite server",
        "l_first": "first finish",
        "l_hours": "hours past year",
        "l_bytype": "points by map type",
        "l_last": "recent finishes",
        "l_map": "map",
        "l_gametype": "gametype",
        "l_region": "region",
        "l_version": "version",
        "l_players": "players",
        "l_type": "type",
        "l_difficulty": "difficulty",
        "l_mapper": "mapper",
        "l_release": "release",
        "l_finishes": "finishes",
        "l_finishers": "finishers",
        "l_median": "median time",
        "l_toprank": "top ranks",
        "l_byregion": "players by region",
        "l_bygametype": "players by gametype",
        "l_topmaps": "most populated maps",
        "l_totalservers": "total servers",
        "l_occupied": "with players",
        "unranked": "unranked",
        "h_player": "player name to show stats for",
        "h_p": "player name (may contain spaces)",
        "h_servers": "print the server list and exit",
        "h_overview": "print a master-server overview and exit",
        "h_find": "find which servers a player is on right now",
        "h_compare": "compare two players",
        "h_map": "show info for a map",
        "h_theme": "color theme",
        "h_filter": "filter servers by substring",
        "h_limit": "how many servers to show (default 40)",
        "h_json": "print raw JSON",
        "h_nocolor": "disable color",
        "h_listthemes": "list available themes and exit",
        "desc": "ddtui \u2014 ASCII DDNet dashboard: stats, servers, overview, find, compare and maps.",
        "epilog": "With no arguments an interactive menu opens.",
        "curses_required": "curses module required (or run with an argument, e.g.: ddtui.py nameless)",
    },
}


def t(key):
    table = STR.get(LANG, STR["en"])
    return table.get(key, STR["en"].get(key, key))


# --------------------------------------------------------------------------- #
# Themes / ANSI (non-interactive output)                                      #
# --------------------------------------------------------------------------- #

RESET = "\x1b[0m"

THEMES = {
    # name: (border, title, label, value, accent, dim)
    "ddnet":      ("39", "81;1", "45", "97", "118", "240"),
    "matrix":     ("34", "46;1", "40", "82", "118", "240"),
    "amber":      ("94", "214;1", "136", "223", "208", "240"),
    "nord":       ("66", "110;1", "73", "189", "152", "240"),
    "mono":       ("244", "255;1", "250", "255", "248", "240"),
    "dracula":    ("141", "212;1", "117", "253", "84", "240"),
    "gruvbox":    ("172", "214;1", "109", "223", "142", "240"),
    "tokyonight": ("61", "111;1", "75", "253", "158", "240"),
    "solarized":  ("37", "33;1", "244", "230", "136", "240"),
    "synthwave":  ("201", "213;1", "99", "219", "51", "240"),
    "ocean":      ("31", "39;1", "37", "195", "80", "240"),
    "crimson":    ("124", "196;1", "131", "224", "203", "240"),
    "forest":     ("28", "40;1", "65", "194", "113", "240"),
    "grape":      ("55", "135;1", "98", "225", "171", "240"),
    "coffee":     ("94", "180;1", "137", "223", "173", "240"),
    "ice":        ("45", "159;1", "117", "195", "87", "240"),
}


def sgr256(code):
    return "\x1b[38;5;%sm" % code


class Style:
    def __init__(self, theme="ddnet", color=True):
        border, title, label, value, accent, dim = THEMES.get(theme, THEMES["ddnet"])
        self.color = color
        self._b, self._t, self._l = border, title, label
        self._v, self._a, self._d = value, accent, dim

    def _w(self, code, text):
        if not self.color:
            return text
        parts = code.split(";")
        if len(parts) == 2 and parts[1] == "1":
            return "\x1b[1m" + sgr256(parts[0]) + text + RESET
        return sgr256(code) + text + RESET

    def border(self, x): return self._w(self._b, x)
    def title(self, x):  return self._w(self._t, x)
    def label(self, x):  return self._w(self._l, x)
    def value(self, x):  return self._w(self._v, x)
    def accent(self, x): return self._w(self._a, x)
    def dim(self, x):    return self._w(self._d, x)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(s):
    return _ANSI_RE.sub("", s)


def char_width(ch):
    if unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def vis_width(s):
    return sum(char_width(c) for c in strip_ansi(s))


def pad(s, width):
    extra = width - vis_width(s)
    return s + " " * extra if extra > 0 else s


def truncate_visible(s, width):
    if vis_width(s) <= width:
        return s
    out, used, i = [], 0, 0
    while i < len(s):
        m = _ANSI_RE.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        ch = s[i]
        w = char_width(ch)
        if used + w > width - 1:
            out.append("\u2026")
            break
        out.append(ch)
        used += w
        i += 1
    out.append(RESET)
    return "".join(out)


def render_box(style, title, lines, width=70):
    inner = width - 2
    bar_used = 2 + 1 + vis_width(title) + 1
    fill = max(0, inner - (bar_used - 1))
    top = (style.border("\u256d\u2500 ") + style.title(title) + " "
           + style.border("\u2500" * fill + "\u256e"))
    out = [top]
    for ln in lines:
        ln = truncate_visible(ln, inner - 2)
        out.append(style.border("\u2502") + " " + pad(ln, inner - 2) + " " + style.border("\u2502"))
    out.append(style.border("\u2570" + "\u2500" * inner + "\u256f"))
    return "\n".join(out)


def supports_color(force_no=False):
    if force_no or os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


# --------------------------------------------------------------------------- #
# HTTP                                                                        #
# --------------------------------------------------------------------------- #

def http_json(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", "replace"))


def fetch_player(name, timeout=12):
    return http_json(PLAYER_API + urllib.parse.quote(name), timeout=timeout)


def fetch_servers(timeout=15):
    data = http_json(SERVERS_API, timeout=timeout)
    return data.get("servers", []) if isinstance(data, dict) else []


def fetch_map(name, timeout=12):
    return http_json(MAPS_API + urllib.parse.quote(name), timeout=timeout)


# --------------------------------------------------------------------------- #
# Formatting helpers                                                          #
# --------------------------------------------------------------------------- #

def fmt_time(seconds):
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    if h:
        return "%d:%02d:%05.2f" % (h, m, s)
    return "%d:%05.2f" % (m, s)


def fmt_date(ts):
    try:
        return time.strftime("%Y-%m-%d", time.localtime(int(ts)))
    except (TypeError, ValueError, OSError):
        return "?"


def rank_str(block):
    """block like {"rank": int|None, "points": int}."""
    if not isinstance(block, dict):
        return t("unranked")
    rank = block.get("rank")
    pts = block.get("points")
    if rank in (None, 0):
        return t("unranked")
    if pts is not None:
        return "#%s (%s %s)" % (rank, pts, t("l_points"))
    return "#%s" % rank


def _addr_host_port(addresses):
    """Pick a friendly ip:port out of the address list."""
    for a in addresses or []:
        m = re.search(r"//(.+)$", a)
        host = m.group(1) if m else a
        return host
    return "?"


def server_summary(srv):
    info = srv.get("info", {}) if isinstance(srv, dict) else {}
    clients = info.get("clients", []) or []
    real = [c for c in clients if c.get("is_player", True)]
    return {
        "name": info.get("name", "?"),
        "map": (info.get("map", {}) or {}).get("name", "?"),
        "gametype": info.get("game_type", "?"),
        "region": srv.get("location", "") or "?",
        "version": info.get("version", "?"),
        "players": len(real),
        "spectators": len(clients) - len(real),
        "max": info.get("max_players", info.get("max_clients", "?")),
        "passworded": bool(info.get("passworded", False)),
        "addr": _addr_host_port(srv.get("addresses", [])),
        "clients": clients,
    }


def sort_servers(servers):
    summ = [(server_summary(s), s) for s in servers]
    summ.sort(key=lambda x: (-x[0]["players"], x[0]["name"].lower()))
    return summ


def fuzzy_match(query, *fields):
    q = query.lower().strip()
    if not q:
        return True
    hay = " ".join(str(f) for f in fields).lower()
    if q in hay:
        return True
    it = iter(hay)
    return all(ch in it for ch in q)


# --------------------------------------------------------------------------- #
# Aggregations (pure, offline-testable)                                       #
# --------------------------------------------------------------------------- #

def master_overview(servers):
    """Aggregate the master server list into a summary dict."""
    total = 0
    occupied = 0
    players = 0
    by_region = {}
    by_gametype = {}
    by_map = {}
    for srv in servers:
        s = server_summary(srv)
        total += 1
        p = s["players"]
        if p > 0:
            occupied += 1
        players += p
        region = str(s["region"]).upper()
        by_region[region] = by_region.get(region, 0) + p
        by_gametype[s["gametype"]] = by_gametype.get(s["gametype"], 0) + p
        if p > 0:
            by_map[s["map"]] = by_map.get(s["map"], 0) + p
    return {
        "servers": total,
        "occupied": occupied,
        "players": players,
        "by_region": by_region,
        "by_gametype": by_gametype,
        "by_map": by_map,
    }


def find_player_servers(servers, name):
    """Return list of (summary, matched_client) where a client matches name."""
    needle = name.lower().strip()
    hits = []
    for srv in servers:
        s = server_summary(srv)
        for c in s["clients"]:
            cname = str(c.get("name", ""))
            if needle and needle in cname.lower():
                hits.append((s, c))
    hits.sort(key=lambda x: (-x[0]["players"], x[0]["name"].lower()))
    return hits


def _top(counter, n=10):
    items = [(k, v) for k, v in counter.items() if v > 0]
    items.sort(key=lambda kv: (-kv[1], str(kv[0]).lower()))
    return items[:n]


def difficulty_stars(diff):
    try:
        d = int(diff)
    except (TypeError, ValueError):
        return "?"
    d = max(0, min(5, d))
    return "\u2605" * d + "\u2606" * (5 - d)


# --------------------------------------------------------------------------- #
# Plain-text report builders (shared by CLI + curses)                         #
# --------------------------------------------------------------------------- #

def player_report_lines(style, data):
    """Return a list of already-styled text lines (no box) for a player."""
    name = data.get("player", "?")
    pts = data.get("points", {}) or {}
    lines = []

    def kv(label_key, value, accent=False):
        v = style.accent(value) if accent else style.value(value)
        lines.append(style.label(pad(t(label_key), 16)) + " " + v)

    total = pts.get("total")
    cur = pts.get("points")
    crank = pts.get("rank")
    head = "%s" % (cur if cur is not None else "?")
    if crank:
        head += "  (#%s" % crank
        if total:
            head += " / %s" % total
        head += ")"
    kv("l_points", head, accent=True)
    kv("l_global", rank_str(data.get("rank")))
    kv("l_team", rank_str(data.get("team_rank")))
    kv("l_year", rank_str(data.get("points_last_year")))
    kv("l_month", rank_str(data.get("points_last_month")))
    kv("l_week", rank_str(data.get("points_last_week")))
    fav = data.get("favorite_server")
    if isinstance(fav, dict) and fav.get("server"):
        kv("l_fav", str(fav.get("server")))
    hours = data.get("hours_played_past_365_days")
    if hours:
        kv("l_hours", str(hours))
    ff = data.get("first_finish")
    if isinstance(ff, dict) and ff.get("map"):
        kv("l_first", "%s \u2014 %s (%s)" % (fmt_date(ff.get("timestamp")), ff.get("map"), fmt_time(ff.get("time"))))
    return name, lines


def player_types_lines(style, data):
    types = data.get("types", {}) or {}
    out = []
    for tname, tinfo in types.items():
        if not isinstance(tinfo, dict):
            continue
        p = tinfo.get("points", {}) or {}
        pts = p.get("points")
        rank = p.get("rank")
        nmaps = len(tinfo.get("maps", {}) or {})
        seg = style.label(pad(tname, 12)) + " " + style.value("%s %s" % (pts if pts is not None else 0, t("l_points")))
        if rank:
            seg += style.dim("  #%s" % rank)
        seg += style.dim("  \u00b7 %d maps" % nmaps)
        out.append(seg)
    return out


def player_finishes_lines(style, data, limit=12):
    fins = data.get("last_finishes", []) or []
    out = []
    for f in fins[:limit]:
        if not isinstance(f, dict):
            continue
        out.append(
            style.dim(fmt_date(f.get("timestamp"))) + "  "
            + style.label(pad(str(f.get("type", "?")), 9)) + " "
            + style.value(pad(str(f.get("map", "?")), 22)) + " "
            + style.accent(fmt_time(f.get("time")))
        )
    return out


def server_detail_lines(style, srv):
    s = server_summary(srv)
    out = []
    out.append(style.label(pad(t("l_map"), 12)) + " " + style.accent(s["map"]))
    out.append(style.label(pad(t("l_gametype"), 12)) + " " + style.value(s["gametype"]))
    out.append(style.label(pad(t("l_region"), 12)) + " " + style.value(str(s["region"]).upper()))
    out.append(style.label(pad(t("l_version"), 12)) + " " + style.dim(str(s["version"])))
    out.append(style.label(pad("addr", 12)) + " " + style.dim(s["addr"]))
    cap = "%s / %s" % (s["players"], s["max"])
    if s["spectators"]:
        cap += style.dim("  (+%d spec)" % s["spectators"])
    out.append(style.label(pad(t("l_players"), 12)) + " " + style.accent(cap))
    if s["passworded"]:
        out.append(style.dim("  \U0001f512 password protected"))
    out.append("")
    for c in s["clients"]:
        nm = c.get("name", "?")
        clan = c.get("clan", "") or ""
        score = c.get("score")
        spec = "" if c.get("is_player", True) else style.dim(" [spec]")
        line = "  " + style.value(pad(nm, 20))
        if clan:
            line += style.dim(pad(clan, 14))
        else:
            line += " " * 14
        if score is not None and score not in (-9999, 9999):
            line += style.accent(fmt_time(score) if str(score).lstrip("-").isdigit() and int(score) > 1000 else str(score))
        line += spec
        out.append(line)
    return s["name"], out


def overview_report_lines(style, servers):
    ov = master_overview(servers)
    out = []
    out.append(style.label(pad(t("l_totalservers"), 18)) + " " + style.accent(str(ov["servers"]))
               + style.dim("  (%d %s)" % (ov["occupied"], t("l_occupied"))))
    out.append(style.label(pad(t("players_online"), 18)) + " " + style.accent(str(ov["players"])))
    out.append("")
    out.append(style.title(t("l_byregion").upper()))
    for region, n in _top(ov["by_region"], 12):
        out.append("  " + style.label(pad(str(region), 8)) + " " + style.value(str(n)))
    out.append("")
    out.append(style.title(t("l_bygametype").upper()))
    for gt, n in _top(ov["by_gametype"], 12):
        out.append("  " + style.label(pad(str(gt), 18)) + " " + style.value(str(n)))
    out.append("")
    out.append(style.title(t("l_topmaps").upper()))
    for mp, n in _top(ov["by_map"], 12):
        out.append("  " + style.value(pad(str(mp), 24)) + " " + style.accent(str(n)))
    return out


def find_report_lines(style, servers, name):
    hits = find_player_servers(servers, name)
    out = []
    for s, c in hits:
        spec = style.dim(" [spec]") if not c.get("is_player", True) else ""
        out.append(
            style.accent(pad(str(c.get("name", "?")), 18)) + " "
            + style.dim(pad(str(s["region"]).upper(), 5)) + " "
            + style.value(pad(str(s["name"]), 30)) + " "
            + style.label(str(s["map"])) + spec
        )
    return hits, out


def compare_report_lines(style, d1, d2):
    n1 = d1.get("player", "?")
    n2 = d2.get("player", "?")

    def cell(block, key="points"):
        if not isinstance(block, dict):
            return "-"
        rank = block.get("rank")
        pts = block.get(key)
        if rank in (None, 0):
            return t("unranked")
        if pts is not None:
            return "#%s (%s)" % (rank, pts)
        return "#%s" % rank

    rows = [
        (t("l_points"), str((d1.get("points", {}) or {}).get("points", "?")),
         str((d2.get("points", {}) or {}).get("points", "?"))),
        (t("l_global"), cell(d1.get("rank")), cell(d2.get("rank"))),
        (t("l_team"), cell(d1.get("team_rank")), cell(d2.get("team_rank"))),
        (t("l_year"), cell(d1.get("points_last_year")), cell(d2.get("points_last_year"))),
        (t("l_month"), cell(d1.get("points_last_month")), cell(d2.get("points_last_month"))),
        (t("l_week"), cell(d1.get("points_last_week")), cell(d2.get("points_last_week"))),
        (t("l_hours"), str(d1.get("hours_played_past_365_days", "-")),
         str(d2.get("hours_played_past_365_days", "-"))),
    ]
    out = []
    out.append(style.label(pad("", 16)) + " "
               + style.accent(pad(str(n1), 20)) + " " + style.accent(pad(str(n2), 20)))
    out.append("")
    for label, a, b in rows:
        out.append(style.label(pad(label, 16)) + " "
                   + style.value(pad(a, 20)) + " " + style.value(pad(b, 20)))
    return n1, n2, out


def map_report_lines(style, data):
    name = data.get("name", "?")
    out = []

    def kv(label_key, value, accent=False):
        v = style.accent(value) if accent else style.value(value)
        out.append(style.label(pad(t(label_key), 14)) + " " + v)

    kv("l_type", str(data.get("type", "?")))
    kv("l_points", str(data.get("points", "?")), accent=True)
    kv("l_difficulty", difficulty_stars(data.get("difficulty")))
    mapper = data.get("mapper")
    if mapper:
        kv("l_mapper", str(mapper))
    rel = data.get("release")
    if rel:
        kv("l_release", fmt_date(rel))
    fin = data.get("finishes")
    if fin is not None:
        kv("l_finishes", str(fin))
    finrs = data.get("finishers")
    if finrs is not None:
        kv("l_finishers", str(finrs))
    med = data.get("median_time")
    if med is not None:
        kv("l_median", fmt_time(med))
    ranks = data.get("ranks", []) or []
    if ranks:
        out.append("")
        out.append(style.title(t("l_toprank").upper()))
        for r in ranks[:10]:
            if not isinstance(r, dict):
                continue
            out.append(
                style.dim(pad("#%s" % r.get("rank", "?"), 5)) + " "
                + style.value(pad(str(r.get("player", "?")), 20)) + " "
                + style.accent(fmt_time(r.get("time")))
            )
    return name, out


# --------------------------------------------------------------------------- #
# Non-interactive (CLI) rendering                                             #
# --------------------------------------------------------------------------- #

def print_player(style, data, width=70):
    name, head = player_report_lines(style, data)
    print()
    print(render_box(style, "PLAYER \u2014 %s" % name, head, width))
    types = player_types_lines(style, data)
    if types:
        print(render_box(style, t("l_bytype").upper(), types, width))
    fins = player_finishes_lines(style, data)
    if fins:
        print(render_box(style, t("l_last").upper(), fins, width))


def print_servers(style, servers, filt=None, limit=40, width=78):
    summ = sort_servers(servers)
    if filt:
        summ = [x for x in summ if fuzzy_match(filt, x[0]["name"], x[0]["map"], x[0]["gametype"])]
    total_players = sum(x[0]["players"] for x in summ)
    lines = []
    for s, _ in summ[:limit]:
        lock = "\U0001f512 " if s["passworded"] else "  "
        cnt = style.accent("%2d/%s" % (s["players"], s["max"]))
        line = (lock + cnt + " "
                + style.dim(pad(str(s["region"]).upper(), 5)) + " "
                + style.value(pad(s["name"], 32)) + " "
                + style.label(pad(s["gametype"], 14)) + " "
                + style.dim(s["map"]))
        lines.append(line)
    title = "SERVERS \u2014 %d (%d %s)" % (len(summ), total_players, t("players_online"))
    print()
    print(render_box(style, title, lines or [style.dim(t("no_servers"))], width))


def print_overview(style, servers, width=58):
    lines = overview_report_lines(style, servers)
    print()
    print(render_box(style, "OVERVIEW", lines, width))


def print_find(style, servers, name, width=72):
    hits, lines = find_report_lines(style, servers, name)
    print()
    if not hits:
        print(render_box(style, "FIND \u2014 %s" % name, [style.dim(t("find_none") % name)], width))
        return
    title = "FIND \u2014 %s (%d)" % (name, len(hits))
    print(render_box(style, title, lines, width))


def print_compare(style, d1, d2, width=62):
    n1, n2, lines = compare_report_lines(style, d1, d2)
    print()
    print(render_box(style, "COMPARE \u2014 %s vs %s" % (n1, n2), lines, width))


def print_map(style, data, width=60):
    name, lines = map_report_lines(style, data)
    print()
    print(render_box(style, "MAP \u2014 %s" % name, lines, width))


# --------------------------------------------------------------------------- #
# Curses GUI                                                                   #
# --------------------------------------------------------------------------- #

BACK = object()


def palette_for(theme):
    """Build a curses 256-color palette dict from the THEMES table."""
    border, title, label, value, accent, dim = THEMES.get(theme, THEMES["ddnet"])

    def n(code):
        try:
            return int(str(code).split(";")[0])
        except (TypeError, ValueError):
            return 250

    return {
        "border": n(border), "title": n(title), "label": n(label),
        "value": n(value), "accent": n(accent), "dim": n(dim), "warn": 203,
    }


def interactive(theme):
    try:
        import curses
    except Exception:
        print(t("curses_required"), file=sys.stderr)
        sys.exit(1)

    PALETTE = palette_for(theme)

    def run(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        try:
            curses.set_escdelay(25)
        except Exception:
            pass
        try:
            curses.start_color()
            curses.use_default_colors()
            has_color = curses.COLORS >= 8
            ncolors = curses.COLORS
            npairs = curses.COLOR_PAIRS
        except curses.error:
            has_color, ncolors, npairs = False, 0, 0
        cache = {}

        def cp(col):
            if not has_color or not isinstance(col, int):
                return curses.A_NORMAL
            use = col if col < ncolors else (col % max(1, ncolors - 1)) + 1
            if use >= ncolors:
                return curses.A_BOLD
            if use not in cache:
                idx = len(cache) + 1
                if idx >= npairs:
                    return curses.A_NORMAL
                try:
                    curses.init_pair(idx, use, -1)
                    cache[use] = curses.color_pair(idx)
                except curses.error:
                    return curses.A_NORMAL
            return cache[use]

        ctx = {"cp": cp, "pal": PALETTE}
        while True:
            mode = pick_mode(stdscr, ctx)
            if mode is None:
                return
            if mode == "stats":
                stats_flow(stdscr, ctx)
            elif mode == "servers":
                servers_flow(stdscr, ctx)
            elif mode == "overview":
                overview_flow(stdscr, ctx)
            elif mode == "find":
                find_flow(stdscr, ctx)
            elif mode == "compare":
                compare_flow(stdscr, ctx)
            elif mode == "map":
                map_flow(stdscr, ctx)

    curses.wrapper(run)


def _add(stdscr, y, x, text, attr=0):
    import curses
    h, w = stdscr.getmaxyx()
    if 0 <= y < h:
        try:
            stdscr.addnstr(y, x, text, max(0, w - 1 - x), attr)
        except curses.error:
            pass


def pick_mode(stdscr, ctx):
    import curses
    cp, pal = ctx["cp"], ctx["pal"]
    options = [
        ("stats", t("mode_stats")),
        ("servers", t("mode_servers")),
        ("overview", t("mode_overview")),
        ("find", t("mode_find")),
        ("compare", t("mode_compare")),
        ("map", t("mode_map")),
    ]
    idx = 0
    while True:
        stdscr.erase()
        _add(stdscr, 0, 0, " " + t("mode_title"), cp(pal["title"]) | curses.A_BOLD)
        _add(stdscr, 1, 0, t("mode_hint"), cp(pal["dim"]))
        for i, (val, label) in enumerate(options):
            marker = "\u276f " if i == idx else "  "
            attr = curses.A_REVERSE | curses.A_BOLD if i == idx else cp(pal["value"])
            _add(stdscr, 3 + i, 0, marker + label, attr)
        stdscr.refresh()
        ch = _getch(stdscr)
        if ch in ("\n", "\r"):
            return options[idx][0]
        if ch == "\x1b":
            return None
        if ch == curses.KEY_UP:
            idx = (idx - 1) % len(options)
        elif ch == curses.KEY_DOWN:
            idx = (idx + 1) % len(options)


def _getch(stdscr):
    import curses
    try:
        return stdscr.get_wch()
    except curses.error:
        return None


def prompt_text(stdscr, ctx, title):
    import curses
    cp, pal = ctx["cp"], ctx["pal"]
    curses.curs_set(1)
    buf = ""
    try:
        while True:
            stdscr.erase()
            _add(stdscr, 0, 0, title, cp(pal["title"]) | curses.A_BOLD)
            _add(stdscr, 1, 0, t("prompt_keys"), cp(pal["dim"]))
            _add(stdscr, 3, 0, " \u276f " + buf, curses.A_BOLD)
            stdscr.refresh()
            ch = _getch(stdscr)
            if ch is None:
                continue
            if isinstance(ch, str):
                if ch in ("\n", "\r"):
                    if buf.strip():
                        return buf.strip()
                    continue
                if ch == "\x1b":
                    return None
                if ch in ("\x7f", "\b"):
                    buf = buf[:-1]
                elif ch == "\x15":
                    buf = ""
                elif ch.isprintable():
                    buf += ch
            elif ch == curses.KEY_BACKSPACE:
                buf = buf[:-1]
    finally:
        curses.curs_set(0)


def draw_status(stdscr, ctx, text, color_key="accent"):
    """Draw a transient status line WITHOUT waiting for a keypress."""
    import curses
    cp, pal = ctx["cp"], ctx["pal"]
    stdscr.erase()
    _add(stdscr, 1, 1, text, cp(pal[color_key]) | curses.A_BOLD)
    stdscr.refresh()


def show_message(stdscr, ctx, text, color_key="dim"):
    import curses
    cp, pal = ctx["cp"], ctx["pal"]
    stdscr.erase()
    _add(stdscr, 1, 1, text, cp(pal[color_key]) | curses.A_BOLD)
    _add(stdscr, 3, 1, t("scroll_hint"), cp(pal["dim"]))
    stdscr.refresh()
    while True:
        ch = _getch(stdscr)
        if ch in ("\x1b", "\n", "\r", "q", "Q"):
            return


def scroll_view(stdscr, ctx, header, lines):
    """Generic scrollable pager of pre-rendered (text, color_key) lines."""
    import curses
    cp, pal = ctx["cp"], ctx["pal"]
    top = 0
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        _add(stdscr, 0, 0, " " + header, cp(pal["title"]) | curses.A_BOLD)
        _add(stdscr, 1, 0, t("scroll_hint"), cp(pal["dim"]))
        body_h = max(1, h - 3)
        top = max(0, min(top, max(0, len(lines) - body_h)))
        for row in range(body_h):
            i = top + row
            if i >= len(lines):
                break
            text, ckey = lines[i]
            _add(stdscr, 3 + row, 0, text, cp(pal.get(ckey, pal["value"])))
        if len(lines) > body_h:
            _add(stdscr, h - 1, 0, " %d-%d / %d " % (top + 1, min(len(lines), top + body_h), len(lines)),
                 cp(pal["dim"]))
        stdscr.refresh()
        ch = _getch(stdscr)
        if ch in ("\x1b", "q", "Q"):
            return
        if ch == curses.KEY_UP:
            top -= 1
        elif ch == curses.KEY_DOWN:
            top += 1
        elif ch == curses.KEY_NPAGE:
            top += body_h
        elif ch == curses.KEY_PPAGE:
            top -= body_h
        elif ch == curses.KEY_HOME:
            top = 0
        elif ch == curses.KEY_END:
            top = len(lines)


def stats_flow(stdscr, ctx):
    name = prompt_text(stdscr, ctx, t("prompt_player"))
    if not name:
        return
    draw_status(stdscr, ctx, t("loading"), "accent")
    try:
        data = fetch_player(name)
    except Exception as e:  # noqa: BLE001
        show_message(stdscr, ctx, t("net_error") % e, "warn")
        return
    if not isinstance(data, dict) or not data.get("player"):
        show_message(stdscr, ctx, t("not_found") % name, "warn")
        return
    plain = Style("mono", color=False)
    pname, head = player_report_lines(plain, data)
    lines = [("  " + s, "value") for s in head]
    types = player_types_lines(plain, data)
    if types:
        lines.append(("", "dim"))
        lines.append((t("l_bytype").upper(), "title"))
        lines += [("  " + s, "label") for s in types]
    fins = player_finishes_lines(plain, data)
    if fins:
        lines.append(("", "dim"))
        lines.append((t("l_last").upper(), "title"))
        lines += [("  " + s, "dim") for s in fins]
    scroll_view(stdscr, ctx, "PLAYER \u2014 %s" % pname, lines)


def servers_flow(stdscr, ctx):
    draw_status(stdscr, ctx, t("loading"), "accent")
    try:
        servers = fetch_servers()
    except Exception as e:  # noqa: BLE001
        show_message(stdscr, ctx, t("net_error") % e, "warn")
        return
    summ = sort_servers(servers)
    if not summ:
        show_message(stdscr, ctx, t("no_servers"), "warn")
        return
    while True:
        chosen = pick_server(stdscr, ctx, summ)
        if chosen is None:
            return
        plain = Style("mono", color=False)
        sname, dlines = server_detail_lines(plain, chosen)
        lines = [("  " + strip_ansi(x), "value") for x in dlines]
        scroll_view(stdscr, ctx, "SERVER \u2014 %s" % sname, lines)


def overview_flow(stdscr, ctx):
    draw_status(stdscr, ctx, t("loading"), "accent")
    try:
        servers = fetch_servers()
    except Exception as e:  # noqa: BLE001
        show_message(stdscr, ctx, t("net_error") % e, "warn")
        return
    plain = Style("mono", color=False)
    lines = [("  " + strip_ansi(x), "value") for x in overview_report_lines(plain, servers)]
    scroll_view(stdscr, ctx, "OVERVIEW", lines)


def find_flow(stdscr, ctx):
    name = prompt_text(stdscr, ctx, t("prompt_find"))
    if not name:
        return
    draw_status(stdscr, ctx, t("loading"), "accent")
    try:
        servers = fetch_servers()
    except Exception as e:  # noqa: BLE001
        show_message(stdscr, ctx, t("net_error") % e, "warn")
        return
    plain = Style("mono", color=False)
    hits, slines = find_report_lines(plain, servers, name)
    if not hits:
        show_message(stdscr, ctx, t("find_none") % name, "warn")
        return
    lines = [("  " + strip_ansi(x), "value") for x in slines]
    scroll_view(stdscr, ctx, "FIND \u2014 %s (%d)" % (name, len(hits)), lines)


def compare_flow(stdscr, ctx):
    n1 = prompt_text(stdscr, ctx, t("prompt_cmp1"))
    if not n1:
        return
    n2 = prompt_text(stdscr, ctx, t("prompt_cmp2"))
    if not n2:
        return
    draw_status(stdscr, ctx, t("loading"), "accent")
    try:
        d1 = fetch_player(n1)
        d2 = fetch_player(n2)
    except Exception as e:  # noqa: BLE001
        show_message(stdscr, ctx, t("net_error") % e, "warn")
        return
    if not (isinstance(d1, dict) and d1.get("player")):
        show_message(stdscr, ctx, t("not_found") % n1, "warn")
        return
    if not (isinstance(d2, dict) and d2.get("player")):
        show_message(stdscr, ctx, t("not_found") % n2, "warn")
        return
    plain = Style("mono", color=False)
    a, b, clines = compare_report_lines(plain, d1, d2)
    lines = [("  " + strip_ansi(x), "value") for x in clines]
    scroll_view(stdscr, ctx, "COMPARE \u2014 %s vs %s" % (a, b), lines)


def map_flow(stdscr, ctx):
    name = prompt_text(stdscr, ctx, t("prompt_map"))
    if not name:
        return
    draw_status(stdscr, ctx, t("loading"), "accent")
    try:
        data = fetch_map(name)
    except Exception as e:  # noqa: BLE001
        show_message(stdscr, ctx, t("net_error") % e, "warn")
        return
    if not isinstance(data, dict) or not data.get("name"):
        show_message(stdscr, ctx, t("map_not_found") % name, "warn")
        return
    plain = Style("mono", color=False)
    mname, mlines = map_report_lines(plain, data)
    lines = [("  " + strip_ansi(x), "value") for x in mlines]
    scroll_view(stdscr, ctx, "MAP \u2014 %s" % mname, lines)


def pick_server(stdscr, ctx, summ):
    import curses
    cp, pal = ctx["cp"], ctx["pal"]
    curses.curs_set(1)
    query, idx, top = "", 0, 0
    try:
        while True:
            filt = [x for x in summ if fuzzy_match(query, x[0]["name"], x[0]["map"], x[0]["gametype"])]
            idx = max(0, min(idx, len(filt) - 1)) if filt else 0
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            _add(stdscr, 0, 0, t("srv_pick_title"), cp(pal["title"]) | curses.A_BOLD)
            _add(stdscr, 1, 0, t("srv_pick_hint"), cp(pal["dim"]))
            _add(stdscr, 2, 0, " > " + query, curses.A_BOLD)
            list_h = max(1, h - 4)
            if not filt:
                _add(stdscr, 3, 0, t("srv_none_match"), cp(pal["dim"]))
            else:
                if idx < top:
                    top = idx
                elif idx >= top + list_h:
                    top = idx - list_h + 1
                for row in range(top, min(len(filt), top + list_h)):
                    s = filt[row][0]
                    marker = "\u276f " if row == idx else "  "
                    lock = "\U0001f512" if s["passworded"] else " "
                    label = "%s%2d/%s %-5s %-30s %s" % (
                        lock, s["players"], s["max"], str(s["region"]).upper()[:5],
                        s["name"][:30], s["map"])
                    attr = cp(pal["value"])
                    if row == idx:
                        attr = curses.A_REVERSE | curses.A_BOLD
                    _add(stdscr, 3 + (row - top), 0, marker + label, attr)
                _add(stdscr, h - 1, 0, " %d/%d " % (len(filt), len(summ)), cp(pal["dim"]))
            stdscr.refresh()
            ch = _getch(stdscr)
            if ch is None:
                continue
            if isinstance(ch, str):
                if ch in ("\n", "\r"):
                    if filt:
                        return filt[idx][1]
                    continue
                if ch == "\x1b":
                    return None
                if ch in ("\x7f", "\b"):
                    query, idx = query[:-1], 0
                elif ch == "\x15":
                    query, idx = "", 0
                elif ch.isprintable():
                    query, idx = query + ch, 0
            else:
                if ch == curses.KEY_UP:
                    idx -= 1
                elif ch == curses.KEY_DOWN:
                    idx += 1
                elif ch == curses.KEY_NPAGE:
                    idx += list_h
                elif ch == curses.KEY_PPAGE:
                    idx -= list_h
                elif ch == curses.KEY_BACKSPACE:
                    query, idx = query[:-1], 0
            if filt:
                idx %= len(filt)
    finally:
        curses.curs_set(0)


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #

def build_parser():
    p = argparse.ArgumentParser(prog="ddtui", description=t("desc"), epilog=t("epilog"))
    p.add_argument("player", nargs="*", help=t("h_player"))
    p.add_argument("-p", "--player", dest="player_opt", help=t("h_p"))
    p.add_argument("-s", "--servers", action="store_true", help=t("h_servers"))
    p.add_argument("-o", "--overview", action="store_true", help=t("h_overview"))
    p.add_argument("--find", help=t("h_find"))
    p.add_argument("-c", "--compare", nargs=2, metavar=("NAME1", "NAME2"), help=t("h_compare"))
    p.add_argument("--map", dest="map_name", help=t("h_map"))
    p.add_argument("-f", "--filter", help=t("h_filter"))
    p.add_argument("-n", "--limit", type=int, default=40, help=t("h_limit"))
    p.add_argument("--theme", default="ddnet", choices=sorted(THEMES.keys()), help=t("h_theme"))
    p.add_argument("--list-themes", action="store_true", help=t("h_listthemes"))
    p.add_argument("--json", action="store_true", help=t("h_json"))
    p.add_argument("--no-color", action="store_true", help=t("h_nocolor"))
    p.add_argument("--version", action="version", version="ddtui " + __version__)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    color = supports_color(force_no=args.no_color)
    style = Style(args.theme, color=color)

    if args.list_themes:
        print("Available themes: " + ", ".join(sorted(THEMES.keys())))
        return 0

    name = args.player_opt or (" ".join(args.player).strip() if args.player else "")

    if args.overview:
        try:
            servers = fetch_servers()
        except Exception as e:  # noqa: BLE001
            print(t("net_error") % e, file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(master_overview(servers), indent=2, ensure_ascii=False))
        else:
            print_overview(style, servers)
        return 0

    if args.find:
        try:
            servers = fetch_servers()
        except Exception as e:  # noqa: BLE001
            print(t("net_error") % e, file=sys.stderr)
            return 1
        if args.json:
            hits = [{"server": s["name"], "region": s["region"], "map": s["map"],
                     "player": c.get("name")} for s, c in find_player_servers(servers, args.find)]
            print(json.dumps(hits, indent=2, ensure_ascii=False))
        else:
            print_find(style, servers, args.find)
        return 0

    if args.compare:
        n1, n2 = args.compare
        try:
            d1 = fetch_player(n1)
            d2 = fetch_player(n2)
        except Exception as e:  # noqa: BLE001
            print(t("net_error") % e, file=sys.stderr)
            return 1
        if not (isinstance(d1, dict) and d1.get("player")):
            print(t("not_found") % n1, file=sys.stderr)
            return 2
        if not (isinstance(d2, dict) and d2.get("player")):
            print(t("not_found") % n2, file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps({"a": d1, "b": d2}, indent=2, ensure_ascii=False))
        else:
            print_compare(style, d1, d2)
        return 0

    if args.map_name:
        try:
            data = fetch_map(args.map_name)
        except Exception as e:  # noqa: BLE001
            print(t("net_error") % e, file=sys.stderr)
            return 1
        if not isinstance(data, dict) or not data.get("name"):
            print(t("map_not_found") % args.map_name, file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print_map(style, data)
        return 0

    if args.servers:
        try:
            servers = fetch_servers()
        except Exception as e:  # noqa: BLE001
            print(t("net_error") % e, file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(servers, indent=2, ensure_ascii=False))
        else:
            print_servers(style, servers, filt=args.filter, limit=args.limit)
        return 0

    if name:
        try:
            data = fetch_player(name)
        except Exception as e:  # noqa: BLE001
            print(t("net_error") % e, file=sys.stderr)
            return 1
        if not isinstance(data, dict) or not data.get("player"):
            print(t("not_found") % name, file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print_player(style, data)
        return 0

    if sys.stdin.isatty() and sys.stdout.isatty():
        interactive(args.theme)
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
