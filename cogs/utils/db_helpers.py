import sqlite3

# --- Connection Helper ---
def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect('zilantia.db')
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
    """Fetches the active character for a Discord user, including origin and faction names."""
    conn = get_db_connection()
    character = conn.execute("""
        SELECT
            c.*,
            o.name as origin_name,
            f.name as faction_name
        FROM
            characters c
        JOIN
            players p ON c.player_id = p.id
        JOIN
            origins o ON c.origin_id = o.id
        LEFT JOIN
            factions f ON c.faction_id = f.id
        WHERE
            p.user_id = ? AND p.active_character_id = c.id
    """, (discord_id,)).fetchone()
    conn.close()
    return character

def get_character_by_name_for_player(player_id: int, name: str):
    """Fetches a character by name for a specific player."""
    conn = get_db_connection()
    character = conn.execute("SELECT * FROM characters WHERE player_id = ? AND name = ?", (player_id, name)).fetchone()
    conn.close()
    return character

def get_character_by_name_global(name: str):
    """Fetches a character by name regardless of owner."""
    conn = get_db_connection()
    character = conn.execute("SELECT * FROM characters WHERE name = ?", (name,)).fetchone()
    conn.close()
    return character

def get_player_characters(player_id: int):
    """Fetches all characters for a specific player."""
    conn = get_db_connection()
    characters = conn.execute("SELECT * FROM characters WHERE player_id = ?", (player_id,)).fetchall()
    conn.close()
    return characters

def get_all_origins():
    """Fetches all available origins from the database."""
    conn = get_db_connection()
    origins = conn.execute("SELECT * FROM origins ORDER BY name").fetchall()
    conn.close()
    return origins

def get_all_factions():
    """Fetches all available factions from the database."""
    conn = get_db_connection()
    factions = conn.execute("SELECT * FROM factions ORDER BY name").fetchall()
    conn.close()
    return factions

# --- Territory Helpers ---
def get_territory_by_name_for_character(character_id: int, name: str):
    """Fetches a territory by name for a specific character."""
    conn = get_db_connection()
    territory = conn.execute("SELECT * FROM territories WHERE owner_character_id = ? AND name = ?", (character_id, name)).fetchone()
    conn.close()
    return territory

def get_character_territory(character_id: int):
    """Fetches the territory owned by a character."""
    conn = get_db_connection()
    territory = conn.execute("SELECT * FROM territories WHERE owner_character_id = ?", (character_id,)).fetchone()
    conn.close()
    return territory

def get_territory_by_name_global(name: str):
    """Fetches a territory by name regardless of owner."""
    conn = get_db_connection()
    territory = conn.execute("SELECT * FROM territories WHERE name = ?", (name,)).fetchone()
    conn.close()
    return territory
