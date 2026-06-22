# ddtui

![python](https://img.shields.io/badge/python-3.7%2B-blue) ![deps](https://img.shields.io/badge/dependencies-0-success) ![license](https://img.shields.io/badge/license-MIT-green) ![platform](https://img.shields.io/badge/platform-terminal-lightgrey)

**ASCII / curses dashboard for [DDraceNetwork](https://ddnet.org) (DDNet), right in your terminal.**

Two tools in one interactive menu (just like [`iuse`](https://github.com/wetair1/iuse)):

- **STATS** — look up a player: points, global & team ranks, points last year/month/week, points by map type, recent finishes, favorite server.
- **SERVERS** — live server browser: fuzzy-search online servers, see map, gametype, region and the players currently online.

Zero dependencies, pure Python 3 standard library. Auto-localized **RU / EN**.

---

## Install

```bash
git clone https://github.com/wetair1/ddtui
cd ddtui
chmod +x ddtui.py
```

No `pip install` needed — it only uses the standard library.

Optional, run it from anywhere:

```bash
ln -s "$PWD/ddtui.py" ~/.local/bin/ddtui
```

## Usage

```bash
# Interactive GUI (arrow keys, live search) — the default:
python3 ddtui.py

# Direct player lookup:
python3 ddtui.py nameless tee
python3 ddtui.py -p "Cor"

# Server browser (non-interactive dump):
python3 ddtui.py --servers
python3 ddtui.py --servers --filter ger --limit 20

# Raw JSON for scripting:
python3 ddtui.py -p "Cor" --json
python3 ddtui.py --servers --json
```

### The GUI

Running with no arguments opens the interactive menu:

```
ddtui — what do you want?
 ↑↓ · Enter — select · Esc — quit

❯ Player stats
  Server browser (online)
```

- **Player stats** → type a name → scrollable stats card.
- **Server browser** → type to fuzzy-search the live server list → Enter to see map, gametype and the player list.

## Options

| Flag | Description |
|------|-------------|
| `player...` | player name to look up (positional, may contain spaces) |
| `-p, --player` | player name |
| `-s, --servers` | print the server list and exit |
| `-f, --filter` | filter servers by substring |
| `-n, --limit` | how many servers to show (default 40) |
| `--theme` | color theme: `ddnet`, `matrix`, `amber`, `nord`, `mono` |
| `--json` | print raw JSON |
| `--no-color` | disable color (also respects `NO_COLOR`) |
| `--version` | print version |

## Data sources

- Player stats: `https://ddnet.org/players/?json2=<name>`
- Server list: `https://master1.ddnet.org/ddnet/15/servers.json`

These are public DDNet endpoints. Be nice and don't hammer them.

## License

MIT — see [LICENSE](LICENSE).

---

<details>
<summary>🇷🇺 Русский</summary>

## ddtui

**ASCII / curses дашборд для [DDraceNetwork](https://ddnet.org) (DDNet) прямо в терминале.**

Два инструмента в одном интерактивном меню (как в [`iuse`](https://github.com/wetair1/iuse)):

- **СТАТИСТИКА** — игрок: очки, мировой и командный ранги, очки за год/месяц/неделю, очки по типам карт, последние финиши, любимый сервер.
- **СЕРВЕРЫ** — живой браузер серверов: нечёткий поиск онлайн-серверов, карта, режим, регион и игроки онлайн.

Без зависимостей, только стандартная библиотека Python 3. Автолокализация **RU / EN** (по `LANG`).

### Установка

```bash
git clone https://github.com/wetair1/ddtui
cd ddtui
python3 ddtui.py
```

### Использование

```bash
python3 ddtui.py                 # интерактивное меню (GUI)
python3 ddtui.py nameless tee     # сразу статистика игрока
python3 ddtui.py --servers        # список серверов
python3 ddtui.py --servers -f ger # фильтр по подстроке
python3 ddtui.py -p "Cor" --json  # сырой JSON
```

В GUI: стрелки ↑↓, Enter — выбрать, Esc — назад/выход. В браузере серверов печатай — идёт живой нечёткий поиск.

Темы: `--theme ddnet|matrix|amber|nord|mono`. Цвет отключается `--no-color` или `NO_COLOR`.

### Источники данных

- Игрок: `https://ddnet.org/players/?json2=<имя>`
- Серверы: `https://master1.ddnet.org/ddnet/15/servers.json`

Лицензия: MIT.

</details>
