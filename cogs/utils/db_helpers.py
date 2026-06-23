import sqlite3

# --- Connection Helper ---
def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect('aetheris.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Player Helpers ---
def get_player_by_discord_id(discord_id: int):
    """Fetches a player record using their Discord ID."""
    conn = get_db_connection()
    player = conn.execute("SELECT * FROM players WHERE user_id = ?", (discord_id,)).fetchone()
    conn.close()
    return player

def create_player(discord_id: int, discord_name: str):
    """Creates a new player record."""
    conn = get_db_connection()
    conn.execute("INSERT INTO players (user_id, user_name) VALUES (?, ?)", (discord_id, discord_name))
    conn.commit()
    conn.close()
    return get_player_by_discord_id(discord_id)

# --- Character Helpers ---
def get_active_character(discord_id: int):
    """Fetches the active character for a Discord user with all stats."""
    conn = get_db_connection()
    character = conn.execute("""
        SELECT c.*, f.name as faction_name, z.name as zone_name
        FROM characters c
        JOIN players p ON c.player_id = p.id
        LEFT JOIN factions f ON c.faction_id = f.id
        LEFT JOIN zones z ON c.zone_id = z.id
        WHERE p.user_id = ? AND p.active_character_id = c.id
    """, (discord_id,)).fetchone()
    conn.close()
    return character

def get_character_by_name_for_player(player_id: int, name: str):
    """Fetches a character by name for a specific player."""
    conn = get_db_connection()
    character = conn.execute("SELECT * FROM characters WHERE player_id = ? AND name = ?", (player_id, name)).fetchone()
    conn.close()
    return character

def get_player_characters(player_id: int):
    """Fetches all characters for a specific player."""
    conn = get_db_connection()
    characters = conn.execute("SELECT * FROM characters WHERE player_id = ?", (player_id,)).fetchall()
    conn.close()
    return characters

# --- World Helpers ---
def get_factions():
    """Fetches all factions."""
    conn = get_db_connection()
    factions = conn.execute("SELECT * FROM factions").fetchall()
    conn.close()
    return factions

def get_zones():
    """Fetches all zones."""
    conn = get_db_connection()
    zones = conn.execute("SELECT * FROM zones").fetchall()
    conn.close()
    return zones

def get_zone_by_id(zone_id: int):
    """Fetches a zone by ID."""
    conn = get_db_connection()
    zone = conn.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
    conn.close()
    return zone

# --- NPC Helpers ---
def get_npcs():
    """Fetches all NPCs."""
    conn = get_db_connection()
    npcs = conn.execute("SELECT * FROM npcs").fetchall()
    conn.close()
    return npcs

def get_npc_by_name(name: str):
    """Fetches an NPC by name."""
    conn = get_db_connection()
    npc = conn.execute("SELECT * FROM npcs WHERE name = ?", (name,)).fetchone()
    conn.close()
    return npc

# --- Memory Helpers ---
def add_character_memory(character_id: int, action_text: str, consequence_text: str = None):
    """Adds a new entry to the character's memory."""
    conn = get_db_connection()
    conn.execute("INSERT INTO character_memory (character_id, action_text, consequence_text) VALUES (?, ?, ?)",
                 (character_id, action_text, consequence_text))
    conn.commit()
    conn.close()

def get_character_memories(character_id: int, limit: int = 5):
    """Fetches the latest memories for a character."""
    conn = get_db_connection()
    memories = conn.execute("SELECT * FROM character_memory WHERE character_id = ? ORDER BY timestamp DESC LIMIT ?",
                            (character_id, limit)).fetchall()
    conn.close()
    return memories
