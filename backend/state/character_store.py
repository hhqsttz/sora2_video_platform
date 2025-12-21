import json
import os
import logging
from typing import List, Dict, Optional
from config import BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, "data")
CHARACTERS_FILE = os.path.join(DATA_DIR, "characters.json")

logger = logging.getLogger(__name__)

CHARACTERS = []

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def save_characters():
    ensure_data_dir()
    try:
        with open(CHARACTERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(CHARACTERS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save characters: {e}")

def load_characters():
    global CHARACTERS
    if not os.path.exists(CHARACTERS_FILE):
        return

    try:
        with open(CHARACTERS_FILE, 'r', encoding='utf-8') as f:
            CHARACTERS = json.load(f)
        logger.info(f"Loaded {len(CHARACTERS)} characters from disk.")
    except Exception as e:
        logger.error(f"Failed to load characters file: {e}")

def add_character(character_data: Dict):
    CHARACTERS.append(character_data)
    save_characters()

def get_all_characters() -> List[Dict]:
    return CHARACTERS

def delete_character(character_id: str) -> bool:
    global CHARACTERS
    initial_len = len(CHARACTERS)
    CHARACTERS = [c for c in CHARACTERS if str(c.get('id')) != str(character_id)]
    if len(CHARACTERS) < initial_len:
        save_characters()
        return True
    return False

# Initialize
load_characters()
