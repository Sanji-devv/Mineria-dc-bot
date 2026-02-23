# 🎲 Mineria Discord Bot

A specialized Discord bot for **Pathfinder Roleplaying Game (1st Edition)** — character management, dice rolling, loot generation, item market, and server registry tools.

## ⚡ Prefixes

| Prefix | Example |
|--------|---------|
| `!` | `!roll 2d20+5` |
| `!m ` | `!m roll 2d20+5` |
| `!mineria ` | `!mineria roll 2d20+5` |

---

## 🎲 Dice & Quick Commands

| Command | Example | Description |
|---------|---------|-------------|
| `!roll <expr>` | `!roll 4d6k3` | Roll dice. Supports modifiers (`+5`), keep-highest (`k3`), multi-roll (`d20, d6`). |
| `!wiki` | `!wiki` | Show official Mineria & Pathfinder Wiki links. |
| `!help` / `!m` / `!h` | `!help` | Interactive command manual with dropdown navigation. |

---

## 🛠️ Registry & Tools

| Command | Example | Description |
|---------|---------|-------------|
| `!d` / `!dup` | `!d` | **Duplicate Check**: Scans the XP Sheet for players violating the "1 Ranked + 1 Clerk" rule. |
| `!loot generate <CR> [count]` | `!loot generate 5 3` | Generate random loot based on Challenge Rating. |
| `!item listdown <query>` | `!item listdown 500` | Search items ≤ price, by AC, or by name — expensive first. |
| `!item listup <query>` | `!item listup sword` | Same search — cheap first. |
| `!item info <name>` | `!item info Longsword` | Detailed item stats with wiki link. |
| `!item filter <rarity\|stat>` | `!item filter wis` | Filter by rarity (common/rare/…) **or** stat (STR/DEX/WIS/…) — cheap → expensive. |
| `!spell <name>` | `!spell fireball` | Search spell on the Pathfinder d20pfsrd wiki. |
| `!doc [name]` | `!doc rules.pdf` | List or download files from the `files/` directory (fuzzy filename match). |

---

## 👤 Character Management

### Creation Flow
`!char create <race>` → `!char dr <stats>` → *(optional)* `!char add/remove` → `!char save <name>`

| Command | Example | Description |
|---------|---------|-------------|
| `!char create <race>` | `!char create Human` | Start character creation for a given race. |
| `!char dr <stat> <val> …` | `!char dr STR 14 DEX 12 …` | Distribute dice points across all 6 stats. |
| `!char add <stat> <val>` | `!char add STR 2` | Add a temporary stat bonus (e.g. racial flex). |
| `!char remove <stat> <val>` | `!char remove DEX 2` | Remove a temporary stat bonus. |
| `!char save <name>` | `!char save Aragon` | Finalize and save the character. |
| `!rec [open\|close]` | `!rec open` | Toggle automatic class recommendations. |

### Management

| Command | Example | Description |
|---------|---------|-------------|
| `!char info [name]` | `!char info Aragon` | View full character sheet. |
| `!char list` | `!char list` | List all saved characters. |
| `!char edit class <name> <class>` | `!char edit class Aragon Fighter` | Update character class. |
| `!char edit stat <name> <stat> <val>` | `!char edit stat Aragon STR 16` | Manually edit a stat value. |
| `!char rename <old> <new>` | `!char rename Aragon Arthas` | Rename a character. |
| `!char delete <name>` | `!char delete Aragon` | Permanently delete a character. |

---

## ⚙️ Features

- **Duplicate Player Detection** — Enforces 1 Ranked + 1 Clerk rule via live Google Sheet data.
- **Item Market** — Full search suite with price, AC, name, rarity, and stat filters.
- **Character Creation** — Race/class-aware stat rolling with 4d6 drop-lowest.
- **Google Sheet Sync** — Live XP tracking and inventory lookups.
- **Automated Backups** — Daily/weekly backups of the `datas/` folder.
- **Robust Logging** — Detailed logs in `logs/mineria.log`. Errors reported once (no duplicates).

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone <repo-url>

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
echo DISCORD_TOKEN_TEST=your_token_here > .env

# 4. Run
python main.py
```

---

## 📁 Data Structure

| File/Dir | Description |
|----------|-------------|
| `datas/characters.json` | Saved user characters |
| `datas/items.json` | Item database (loot & market) |
| `datas/races.json` | Race definitions & modifiers |
| `datas/classes.json` | Class definitions & primary stats |
| `files/` | Documents served by `!doc` |
| `logs/mineria.log` | Application log (rotating) |