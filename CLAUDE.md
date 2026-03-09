# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A multi-platform chat data analysis tool that converts Telegram and WhatsApp chat exports into normalized CSV files for statistical analysis. The long-term goal is a "Groupchat Wrapped" feature (à la Spotify Wrapped) for personal chat history.

## Setup

Requires Homebrew, Node.js, and pyenv (`brew install pyenv`).

```bash
pyenv install                   # reads .python-version
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

VS Code auto-detects `.venv` as a Jupyter kernel.

## Commands

### Running the converters

```bash
# Telegram: convert HTML export folder to CSV
node tg_convert.js <input-folder>
# Default input folder: ./chats
# Output: ./exports/all_messages.csv

# WhatsApp: convert TXT export to CSV
node wa_convert.js <input-file>
# Example: node wa_convert.js "raw chat data/mino_chat_formatted.txt"
```

### Installing dependencies

```bash
npm install
```

### Running notebooks

Open `tg_explore.ipynb` or `wa_explore.ipynb` in VS Code or Jupyter. Requires pandas installed in the active Python environment.

## Architecture

### Dual-converter pattern

```
Telegram HTML exports  →  tg_convert.js (Puppeteer DOM parsing)  →  exports/all_messages.csv
WhatsApp TXT exports   →  wa_convert.js (regex text parsing)      →  exports/<name>.csv
                                                                          ↓
                                                         tg_explore.ipynb / wa_explore.ipynb
                                                         (pandas analysis & statistics)
```

### tg_convert.js
Uses Puppeteer (headless Chrome) to load and parse Telegram's exported HTML files — not a raw HTML parser. This matters because Telegram's HTML structure requires DOM querying.

- Message container selector: `.message.default.clearfix`
- Sender is inherited from previous message when absent (Telegram groups consecutive messages from same sender)
- Processes multiple `.html` files in a folder alphabetically and concatenates into one CSV
- Output schema: `id, timestamp, sender, text, replyToId`

### wa_convert.js
Text processing pipeline for WhatsApp's `[TIMESTAMP] SENDER: TEXT` export format.

- Multi-line messages: lines not starting with `[` are continuations of the previous message
- Uses `csv-stringify` stream for RFC-4180-compliant CSV output
- Output schema: `date, sender, text` (no message IDs or reply tracking)

### Known issues / TODOs (from README)
- Media messages are not handled
- WhatsApp parser has a line-wrapping bug for messages with embedded newlines
- Reply ID extraction fails when the referenced message is in a different HTML file
- Date parsing in notebooks has format inference issues
- Schema is not yet unified across platforms (Telegram has `id`/`replyToId`, WhatsApp doesn't)

## Data layout

```
raw chat data/     # Raw exports (gitignored)
exports/           # Generated CSVs (gitignored, exports/.gitkeep tracked)
input_example/     # Sample WhatsApp export for testing
```
