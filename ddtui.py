#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddtui - a tiny ASCII / curses dashboard for DDraceNetwork (DDNet).

Two tools in one, picked from an interactive menu (like `iuse`):

  * STATS   - look up a player: points, global / team ranks, points by map
              type, recent finishes, favorite server. (ddnet.org json2 API)
  * SERVERS - live server browser: search online servers, see map, gametype,
              ping region and the players currently online.
              (master1.ddnet.org HTTPS masterserver)

Pure Python 3 standard library, zero dependencies. RU/EN auto-localized.

Usage:
    python3 ddtui.py                 # interactive GUI (menu)
    python3 ddtui.py nameless tee     # direct player lookup
    python3 ddtui.py --servers        # dump the server list
    python3 ddtui.py -p "Cor" --json  # raw JSON for scripting

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

__version__ = "0.1.0"

PLAYER_API = "https://ddnet.org/players/?json2="
SERVERS_API = "https://master1.ddnet.org/ddnet/15/servers.json"
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
        "mode_title": "ddtui \u2014 что смотрим?",
        "mode_hint": " \u2191\u2193 \u00b7 Enter \u2014 выбрать \u00b7 Esc \u2014 выход",
        "mode_stats": "Статистика игрока",
        "mode_servers": "Браузер серверов (онлайн)",
        "prompt_player": " Имя игрока (точное, как в игре):",
        "prompt_keys": " Enter \u2014 искать \u00b7 Esc \u2014 назад",
        "loading": "Загрузка\u2026",
        "net_error": "Ошибка сети: %s",
        "not_found": "Игрок \u00ab%s\u00bb не найден.",
        "no_servers": "Серверы не найдены.",
        "srv_pick_title": " ddtui \u2014 серверы: выбери (Enter \u2014 детали)",
        "srv_pick_hint": " Печатай для поиска \u00b7 \u2191\u2193 \u00b7 Enter \u2014 детали \u00b7 Esc \u2014 назад",
        "srv_none_match": " Ничего не найдено. Измени запрос или Backspace.",
        "scroll_hint": " \u2191\u2193/PgUp/PgDn \u2014 листать \u00b7 Esc \u2014 назад",
        "players_online": "игроков онлайн",
        "cancelled": "Отменено.",
        "l_points": "очки",
        "l_global": "мировой ранг",
        "l_team": "командный ранг",
        "l_year": "за год",
        "l_month": "за месяц",
        "l_week": "за неделю",
        "l_fav": "любимый сервер",
        "l_first": "первый финиш",
        "l_hours": "часов за год",
        "l_bytype": "очки по типам карт",
        "l_last": "последние финиши",
        "l_map": "карта",
        "l_gametype": "режим",
        "l_region": "регион",
        "l_version": "версия",
        "l_players": "игроки",
        "unranked": "без ранга",
        "h_player": "имя игрока для статистики",
        "h_p": "имя игрока (можно с пробелами)",
        "h_servers": "показать список серверов и выйти",
        "h_theme": "цветовая тема",
        "h_filter": "фильтр серверов по подстроке",
        "h_limit": "сколько серверов показать (по умолчанию 40)",
        "h_json": "вывести сырой JSON",
        "h_nocolor": "отключить цвет",
        "desc": "ddtui \u2014 ASCII-дашборд DDNet: статистика игрока + браузер серверов.",
        "epilog": "Без аргументов открывается интерактивное меню.",
        "curses_required": "Нужен модуль curses (или запусти с аргументом, например: ddtui.py nameless)",
    },
    "en": {
        "mode_title": "ddtui \u2014 what do you want?",
        "mode_hint": " \u2191\u2193 \u00b7 Enter \u2014 select \u00b7 Esc \u2014 quit",
        "mode_stats": "Player stats",
        "mode_servers": "Server browser (online)",
        "prompt_player": " Player name (exact, as in game):",
        "prompt_keys": " Enter \u2014 search \u00b7 Esc \u2014 back",
        "loading": "Loading\u2026",
        "net_error": "Network error: %s",
        "not_found": "Player \u00ab%s\u00bb not found.",
        "no_servers": "No servers found.",
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
        "unranked": "unranked",
        "h_player": "player name to show stats for",
        "h_p": "player name (may contain spaces)",
        "h_servers": "print the server list and exit",
        "h_theme": "color theme",
        "h_filter": "filter servers by substring",
        "h_limit": "how many servers to show (default 40)",
        "h_json": "print raw JSON",
        "h_nocolor": "disable color",
        "desc": "ddtui \u2014 ASCII DDNet dashboard: player stats + server browser.",
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
    "ddnet":  ("39", "81;1", "45", "97", "118", "240"),
    "matrix": ("34", "46;1", "40", "82", "118", "240"),
    "amber":  ("94", "214;1", "136", "223", "208", "240"),
    "nord":   ("66", "110;1", "73", "189", "152", "240"),
    "mono":   ("244", "255;1", "250", "255", "248", "240"),
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


# --------------------------------------------------------------------------- #
# Curses GUI                                                                   #
# --------------------------------------------------------------------------- #

BACK = object()


def interactive(theme):
    try:
        import curses
    except Exception:
        print(t("curses_required"), file=sys.stderr)
        sys.exit(1)

    PALETTE = {
        "border": 39, "title": 81, "label": 45, "value": 250,
        "accent": 118, "dim": 240, "warn": 203,
    }
    if theme == "matrix":
        PALETTE.update(border=34, title=46, label=40, value=82, accent=118)
    elif theme == "amber":
        PALETTE.update(border=94, title=214, label=136, value=223, accent=208)
    elif theme == "nord":
        PALETTE.update(border=66, title=110, label=73, value=189, accent=152)
    elif theme == "mono":
        PALETTE.update(border=244, title=255, label=250, value=252, accent=248)

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
            else:
                servers_flow(stdscr, ctx)

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
    options = [("stats", t("mode_stats")), ("servers", t("mode_servers"))]
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
    show_message(stdscr, ctx, t("loading"), "accent")
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
    show_message(stdscr, ctx, t("loading"), "accent")
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
    p.add_argument("-f", "--filter", help=t("h_filter"))
    p.add_argument("-n", "--limit", type=int, default=40, help=t("h_limit"))
    p.add_argument("--theme", default="ddnet", choices=sorted(THEMES.keys()), help=t("h_theme"))
    p.add_argument("--json", action="store_true", help=t("h_json"))
    p.add_argument("--no-color", action="store_true", help=t("h_nocolor"))
    p.add_argument("--version", action="version", version="ddtui " + __version__)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    color = supports_color(force_no=args.no_color)
    style = Style(args.theme, color=color)

    name = args.player_opt or (" ".join(args.player).strip() if args.player else "")

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
