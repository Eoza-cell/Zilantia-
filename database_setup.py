import sqlite3

def setup_database():
    """
    Sets up the SQLite database for the "Ère des Arcanes" world.
    This function replaces the old Zilantia schema and populates the database with initial data.
    """
    conn = sqlite3.connect('arcanes.db')
    cursor = conn.cursor()

    # --- Drop Old Tables (to ensure a clean slate) ---
    cursor.execute("DROP TABLE IF EXISTS players")
    cursor.execute("DROP TABLE IF EXISTS player_missions")
    cursor.execute("DROP TABLE IF EXISTS locations")
    cursor.execute("DROP TABLE IF EXISTS pnjs")
    cursor.execute("DROP TABLE IF EXISTS items")
    cursor.execute("DROP TABLE IF EXISTS enemies")
    cursor.execute("DROP TABLE IF EXISTS missions")
    cursor.execute("DROP TABLE IF EXISTS active_combats")
    cursor.execute("DROP TABLE IF EXISTS location_exits")

    # --- Create New Tables for "Ère des Arcanes" ---

    # Players Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        user_name TEXT NOT NULL,
        user_avatar_url TEXT,
        rang TEXT DEFAULT 'F',
        pp INTEGER DEFAULT 0, -- Points de Puissance
        luxium INTEGER DEFAULT 100,
        ss_validated BOOLEAN DEFAULT FALSE
    )
    ''')

    # Territories Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS territories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- Village, Ville, Cité, Royaume, Empire
        owner_id INTEGER NOT NULL,
        population INTEGER DEFAULT 10,
        loyalty INTEGER DEFAULT 75, -- out of 100
        army_level INTEGER DEFAULT 1,
        luxium_balance INTEGER DEFAULT 0,
        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES players(user_id)
    )
    ''')

    # PNJ Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pnjs_dynamiques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT,
        loyalty INTEGER,
        hostility INTEGER,
        territory_id INTEGER,
        FOREIGN KEY (territory_id) REFERENCES territories(id)
    )
    ''')

    # Armies Table (Simplified for now)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS armies (
        territory_id INTEGER PRIMARY KEY,
        power INTEGER,
        FOREIGN KEY (territory_id) REFERENCES territories(id)
    )
    ''')

    # Artefacts Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artefacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rarity TEXT,
        effect TEXT,
        owner_id INTEGER,
        FOREIGN KEY (owner_id) REFERENCES players(user_id)
    )
    ''')

    # --- Initial Data Insertion (Optional, for testing) ---
    # You can add initial players or artefacts here if needed for testing.
    # For example:
    # cursor.execute("INSERT INTO players (user_id, user_name) VALUES (123456789, 'TestUser')")

    conn.commit()
    conn.close()
    print("Database `arcanes.db` has been set up for 'Ère des Arcanes'.")

if __name__ == '__main__':
    setup_database()
