# 🎲 Mineria Discord Bot

A specialized Discord bot for **Pathfinder Roleplaying Game (1e)** character management. 

## ⚡ Quick Commands

Prefixes: `!`, `!mineria`, `!m`

| Command | Usage | Description |
|---------|-------|-------------|
| `!help` | `!m` | Display the interactive command manual. |
| `!roll` | `!roll 2d20+5` | Roll dice with modifiers (e.g. `!roll d20`, `!roll 4d6k3`). |
| `!link` | `!link` | Show commonly used Wiki links. |

## 🛠️ Registry & Tools (Google Sheets)

| Command | Usage | Description |
|---------|-------|-------------|
| `!d` | `!d` | **Duplicate Check**: Scans the XP Sheet to find players violating the "1 Ranked + 1 Clerk" limit. |
| `!feat check` | `!feat check <name>` | **Feat Registry**: Checks if a specific Feat/Trait is available in the Global Registry. |
| `!loot generate` | `!loot gen 5 3` | Generates random loot based on CR (Challenge Rating). |
| `!item listdown` | `!item listdown 1000` | Lists top expensive items under a specific gold price. |
| `!doc` | `!doc [name]` | List or download PDF/Word documents from the `files/` directory. |

## 👤 Character Management

| Command | Usage | Description |
|---------|-------|-------------|
| `!char create` | `!char create Human` | Start a new character creation process. |
| `!char dr` | `!char dr STR 10 ...` | Distribute dice points and roll stats. |
| `!char add` | `!char add STR 2` | Add a bonus to a stat (e.g. for Racial flexible traits). |
| `!char save` | `!char save Aragon` | Save the created character to your profile. |
| `!char info` | `!char info [name]` | View your character sheet. |
| `!char list` | `!char list` | List all your saved characters. |
| `!char edit class` | `!char edit class <name> <class>` | Update character class. |
| `!char edit stat` | `!char edit stat <name> val>` | Manually edit a stat. |
| `!char rename` | `!char rename <old> <new>` | Rename a character. |
| `!char delete` | `!char delete <name>` | Delete a character. |
| `!rec` | `!rec open/close` | Toggle AI class recommendations. |

## Features

- **Duplicate Player Detection**: Automatically identifies players holding more characters than allowed (Max 1 Ranked + 1 Clerk).
- **Google Sheet Sync**: Fetches live data for Feat availability and Player XP tracking.
- **Automated Backups**: Daily and weekly backups of the `data/` directory.
- **Robust Logging**: Detailed logs in `logs/mineria.log`.

## Installation

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Create a `.env` file with `DISCORD_TOKEN`.
4. Run: `python main.py`.

## Data Structure

- **data/characters.json**: User profiles.
- **data/items.json**: Item database for Loot/Market.
- **data/races.json` & `classes.json**: Game rules data.