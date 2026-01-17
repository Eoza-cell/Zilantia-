import sqlite3

def setup_database():
    """
    Sets up the SQLite database for the "Zilantia" world with a multi-character architecture.
    """
    conn = sqlite3.connect('zilantia.db')
    cursor = conn.cursor()

    # --- Drop Old Tables for a clean slate ---
    # We drop them in reverse order of creation due to foreign key constraints
    cursor.execute("DROP TABLE IF EXISTS artefacts")
    cursor.execute("DROP TABLE IF EXISTS world_events")
    cursor.execute("DROP TABLE IF EXISTS pnjs_dynamiques")
    cursor.execute("DROP TABLE IF EXISTS territories")
    cursor.execute("DROP TABLE IF EXISTS characters")
    cursor.execute("DROP TABLE IF EXISTS origins")
    cursor.execute("DROP TABLE IF EXISTS factions")
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

    # 2. Factions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS factions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')

    # 3. Origins Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS origins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')

    # 4. Characters Table (Represents an in-game character, linked to a Player, Origin, and Faction)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        luxium INTEGER DEFAULT 100,
        origin_id INTEGER NOT NULL,
        faction_id INTEGER, -- Can be NULL until a faction is chosen
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
        FOREIGN KEY (origin_id) REFERENCES origins(id),
        FOREIGN KEY (faction_id) REFERENCES factions(id) ON DELETE SET NULL
    )
    ''')

    # 5. Territories Table (Owned by a Character)
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

    # 6. PNJ Table (Linked to a Territory)
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

    # 7. Artefacts Table (Owned by a Character)
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

    # 8. World Events Table
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

    # --- Populate Initial Data ---

    # Populate Factions
    factions = ['Astralyon', 'Emberfall', 'Obsidienne', 'Lyr']
    cursor.executemany("INSERT INTO factions (name) VALUES (?)", [(f,) for f in factions])

    # Populate Origins
    origins = [
        'Arcaniste', 'Enchanteur', 'Occultiste', 'Prophète',
        'Guerrier', 'Berserker', 'Chevalier', 'Gladiateur',
        'Ombre', 'Assassin', 'Rôdeur', 'Espion'
    ]
    cursor.executemany("INSERT INTO origins (name) VALUES (?)", [(o,) for o in origins])


    conn.commit()
    conn.close()
    print("Database `zilantia.db` has been set up for Zilantia.")

if __name__ == '__main__':
    setup_database()
