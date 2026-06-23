import sqlite3
import os

def setup_database():
    """
    Sets up the SQLite database for the "Aetheris" world.
    """
    db_file = 'aetheris.db'
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # --- Drop Old Tables ---
    tables = [
        'combat_history', 'character_memory', 'actions', 'events',
        'npcs', 'factions', 'zones', 'characters', 'players'
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # --- Create New Tables ---

    # 1. Players Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        user_name TEXT NOT NULL,
        active_character_id INTEGER,
        FOREIGN KEY (active_character_id) REFERENCES characters(id) ON DELETE SET NULL
    )
    """)

    # 2. Characters Table
    # Stats: STR, AGI, DEF, POW, ACC, END
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        power_type TEXT, -- Électrokinésie, Pyrokinésie, etc.
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,

        -- Stats
        str INTEGER DEFAULT 10,
        agi INTEGER DEFAULT 10,
        def INTEGER DEFAULT 10,
        pow INTEGER DEFAULT 10,
        acc INTEGER DEFAULT 10,
        end INTEGER DEFAULT 10,

        -- State
        hp INTEGER DEFAULT 100,
        max_hp INTEGER DEFAULT 100,
        fatigue INTEGER DEFAULT 0,
        reputation INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Neutre', -- Recherché, Protégé, Neutre

        faction_id INTEGER,
        zone_id INTEGER,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
        FOREIGN KEY (faction_id) REFERENCES factions(id) ON DELETE SET NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL
    )
    """)

    # 3. Factions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        influence INTEGER DEFAULT 0
    )
    """)

    # 4. Zones Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL, -- Surveillée, Corrompue, Instable, Secrète
        description TEXT,
        danger_level INTEGER DEFAULT 1,
        controlling_faction_id INTEGER,
        FOREIGN KEY (controlling_faction_id) REFERENCES factions(id) ON DELETE SET NULL
    )
    """)

    # 5. Character Memory (Log of actions/decisions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS character_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        action_text TEXT NOT NULL,
        consequence_text TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
    )
    """)

    # 6. NPCs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS npcs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT,
        avatar_url TEXT,
        faction_id INTEGER,
        zone_id INTEGER,
        FOREIGN KEY (faction_id) REFERENCES factions(id) ON DELETE SET NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL
    )
    """)

    # 7. Events Table (World Persistence)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        zone_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL
    )
    """)

    # --- Seed Initial Data ---

    # Factions
    factions = [
        ('AEGIS', "Organisation mondiale qui cache l'existence des failles."),
        ('NEON LABS', 'Corporation expérimentant sur les éveillés.'),
        ('BLACK VEIL', 'Syndicat du crime surnaturel.'),
        ('Éveillés Libres', 'Civils, mercenaires et survivants indépendants.')
    ]
    cursor.executemany("INSERT INTO factions (name, description) VALUES (?, ?)", factions)

    # Zones
    zones = [
        ('Centre-Ville', 'Surveillée', 'Le coeur de la métropole, hautement sécurisé par AEGIS.', 1, 1),
        ('Quartier Industriel', 'Corrompue', 'Anciennes usines servant de laboratoires à NEON LABS.', 3, 2),
        ('Les Docks', 'Instable', 'Territoire disputé par BLACK VEIL, failles fréquentes.', 4, 3),
        ('Zone de Faille Alpha', 'Instable', 'Réalité fragmentée, entités non humaines signalées.', 5, None)
    ]
    cursor.executemany("INSERT INTO zones (name, type, description, danger_level, controlling_faction_id) VALUES (?, ?, ?, ?, ?)", zones)

    # NPCs
    npcs = [
        ('Agent K', 'Commandant de terrain AEGIS', 'https://pollinations.ai/p/cool%20secret%20agent%20man%20suit%20cyberpunk', 1, 1),
        ('Dr. Aris', 'Chercheuse en chef NEON LABS', 'https://pollinations.ai/p/female%20scientist%20neon%20glasses', 2, 2),
        ('Vane', 'Chef de gang BLACK VEIL', 'https://pollinations.ai/p/punk%20leader%20shadow%20mask', 3, 3)
    ]
    cursor.executemany("INSERT INTO npcs (name, role, avatar_url, faction_id, zone_id) VALUES (?, ?, ?, ?, ?)", npcs)

    conn.commit()
    conn.close()
    print(f"Database {db_file} has been set up for Aetheris.")

if __name__ == '__main__':
    setup_database()
