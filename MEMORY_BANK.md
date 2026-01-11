# Memory Bank - Mineria DC Bot

## Project Overview
Mineria DC Bot is a specialized Discord utility for the **Pathfinder Roleplaying Game** system. It focuses on character lifecycle management—from racial selection and attribute rolling to profile persistence.

## Technical Architecture
- **Language**: Python 3.x
- **Core Framework**: `discord.py` (Cog-based structure)
- **Data Layer**: JSON-based flat files in the `data/` directory.
- **Shared Logic**: `utils.py` for persistence, `recommender.py` for class logic.
- **Language Policy**: **Strict English**.

## Key Modules
1. **`main.py`**: Entry point. Orchestrates the loading of Cogs.
2. **`character.py`**: Character management Cog. Contains all data persistence and recommendation logic.
3. **`dice.py`**: Dice rolling Cog. Parses expressions like `2d20+5`.
4. **`help.py`**: Custom help system Cog.

## Established Workflows

### Character Creation Flow
1. **Race Selection** (`!char create <race>`): User picks a race, calculating available dice points (40 - Race Points).
2. **Dice Distribution** (`!char dr <stats>`): User spends points across 6 attributes. The bot rolls the specified number of dice and takes the top 3.
3. **Racial Adjustments**: Automatic application of fixed racial modifiers.
4. **Manual Tweaking** (`!char add/remove`): Used for flexible bonuses or manual corrections.
5. **Class Recommendation**: Automatic rule-based suggestions generated after stat distribution using `data/classes.json`.
6. **Persistence** (`!char save <name>`): Finalizes and saves the character to `data/characters.json`.

## Technical Caveats
- **Dice Points**: Base 40 minus the Race Points (RP) defined in `data/races.json`.
- **Attribute Minimum**: Each attribute must be assigned at least 3 dice (mirroring the classic 3d6 approach).

## Roadmap
- [ ] Implement Inventory tracking.
- [ ] Add Level-up mechanics.
- [ ] Integrate Skill point allocation.