# Memory Bank - Mineria DC Bot

## Project Overview
Mineria DC Bot is a specialized Discord utility for **Pathfinder 1st Edition** roleplaying games. It automates character creation, dice rolling, and profile management, providing a seamless experience for players directly within Discord.

## System Architecture

The codebase is refactored into a modular `Cogs` structure:

- **`main.py`**: Application entry point. Handles bot initialization, environment configuration, and extension loading (`dice`, `character`, `help`).
- **`dice.py`**: Specialized module for dice mechanics. Handles parsing and executing standard RPG dice expressions (e.g., `2d20+5`).
- **`character.py`**: Core domain logic for character management. Handles:
  - Character creation workflow (`create`, `distribute`, `save`).
  - Stat generation (Dice pool allocation system).
  - Profile management (`info`, `edit`, `delete`, `rename`).
  - Class recommendations engine.
- **`help.py`**: Dynamic help system that generates documentation based on loaded commands.

## Key Workflows

### Character Creation Flow
1. **Race Selection**: User starts with `!char create <race>`.
   - Bot calculates available "Dice Points" (Base 40 - Race Cost).
2. **Stat Allocation**: User commands `!char dr <str> <dex> <con> <int> <wis> <cha>`.
   - Inputs represent the *number of d6 dice* allocated to each attribute.
   - **Mechanism**: For each stat, the bot rolls `N` d6 and sums the highest 3 dice.
3. **Modifiers**:
   - Racial modifiers (from `races.json`) are automatically applied.
   - User can manually adjust stats with `!char add <stat> <val>` or `!char remove <stat> <val>`.
4. **Finalization**:
   - Class recommendations are shown (if enabled).
   - User saves the character with `!char save <name>`.

### Data Persistence
Data is stored in JSON format within the `data/` directory:
- `characters.json`: Stores all user characters.
- `races.json`: Usage definitions for races (modifiers, point costs).
- `classes.json`: Logic for class recommendations.
- `user_settings.json`: User-specific preferences (e.g., `show_recommendations`).

## Feature Inventory

| Category | Command | Description |
|---|---|---|
| **Dice** | `!roll` | Roll any combination of dice (e.g., `4d6+2`). |
| **Creation** | `!char create` | Begin creation process. |
| | `!char dr` | Distribute dice and roll stats. |
| | `!char add` / `!char remove` | Manually adjust stats during creation. |
| **Profile** | `!char info` | View character sheet. |
| | `!char save` | Save current character. |
| | `!char edit` | Modify saved character data. |
| | `!char delete` | Permanently remove a character. |
| **Settings** | `!rec`, `!m r` | Toggle class recommendations (`open`/`close`). |

## Roadmap & Status
- **Current State**: Fully functional modular bot in English.
- **Recent Updates**:
  - Refactored monolith to modules (`dice`, `character`, `help`).
  - Added toggle for recommendations (`!rec open`/`close`).
  - Implemented stat manual adjustment (`add`/`remove`).
- **Future Goals**:
  - Integration of Generative AI for dynamic character backstories and advanced class suggestions.
  - Inventory management system.
  - Skill point calculation and allocation.