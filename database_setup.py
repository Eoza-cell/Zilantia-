import sqlite3

def setup_database():
    """
    Sets up the SQLite database for the "Ère des Arcanes" world with a multi-character architecture.
    """
    conn = sqlite3.connect('arcanes.db')
    cursor = conn.cursor()

    # --- Drop Old Tables for a clean slate ---
    # We drop them in reverse order of creation due to foreign key constraints
    cursor.execute("DROP TABLE IF EXISTS artefacts")
    cursor.execute("DROP TABLE IF EXISTS world_events")
    cursor.execute("DROP TABLE IF EXISTS pnjs_dynamiques")
    cursor.execute("DROP TABLE IF EXISTS territories")
    cursor.execute("DROP TABLE IF EXISTS characters")
    cursor.execute("DROP TABLE IF EXISTS players")

    # --- Create New Tables ---

    # 1. Players Table (Represents a Discord User)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL, -- Discord User ID
        user_name TEXT NOT NULL,
        active_character_id INTEGER,
        FOREIGN KEY (active_character_id) REFERENCES characters(id) ON DELETE SET NULL
    )
    ''')

    # 2. Characters Table (Represents an in-game character, linked to a Player)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        rang TEXT DEFAULT 'F',
        pp INTEGER DEFAULT 0,
        luxium INTEGER DEFAULT 100,
        ss_validated BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
    )
    ''')

    # 3. Territories Table (Owned by a Character)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS territories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- Village, Ville, Cité, etc.
        owner_character_id INTEGER, -- Can be NULL if abandoned
        population INTEGER DEFAULT 100,
        loyalty INTEGER DEFAULT 75,
        army_level INTEGER DEFAULT 1,
        luxium_balance INTEGER DEFAULT 0,
        FOREIGN KEY (owner_character_id) REFERENCES characters(id) ON DELETE SET NULL
    )
    ''')

    # 4. PNJ Table (Linked to a Territory)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pnjs_dynamiques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT,
        loyalty INTEGER,
        hostility INTEGER,
        territory_id INTEGER,
        FOREIGN KEY (territory_id) REFERENCES territories(id) ON DELETE SET NULL
    )
    ''')

    # 5. Artefacts Table (Owned by a Character)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artefacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rarity TEXT,
        effect TEXT,
        owner_character_id INTEGER, -- Can be NULL if not owned
        FOREIGN KEY (owner_character_id) REFERENCES characters(id) ON DELETE SET NULL
    )
    ''')

    # --- World Events Table ---
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS world_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- boss, rebellion, war, etc.
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()
    print("Database `arcanes.db` has been set up with the new multi-character architecture.")

if __name__ == '__main__':
    setup_database()
