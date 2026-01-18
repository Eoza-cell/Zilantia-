import sqlite3

def setup_database():
    """
    Sets up the SQLite database for the "Zilantia" world with a multi-character architecture.
    """
    conn = sqlite3.connect('zilantia.db')
    cursor = conn.cursor()

    # --- Drop Old Tables for a clean slate ---
    # We drop them in reverse order of creation due to foreign key constraints
    cursor.execute("DROP TABLE IF EXISTS character_quests")
    cursor.execute("DROP TABLE IF EXISTS quests")
    cursor.execute("DROP TABLE IF EXISTS npcs")
    cursor.execute("DROP TABLE IF EXISTS bosses")
    cursor.execute("DROP TABLE IF EXISTS zones")
    cursor.execute("DROP TABLE IF EXISTS character_artefacts")
    cursor.execute("DROP TABLE IF EXISTS artefacts")
    cursor.execute("DROP TABLE IF EXISTS world_events")
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
        hp INTEGER DEFAULT 100, -- Health Points
        attack INTEGER DEFAULT 10, -- Attack Power
        luxium INTEGER DEFAULT 100,
        origin_id INTEGER NOT NULL,
        faction_id INTEGER, -- Can be NULL until a faction is chosen
        current_zone_id INTEGER DEFAULT 1, -- Default to the starting zone
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
        FOREIGN KEY (origin_id) REFERENCES origins(id),
        FOREIGN KEY (faction_id) REFERENCES factions(id) ON DELETE SET NULL,
        FOREIGN KEY (current_zone_id) REFERENCES zones(id)
    )
    ''')

    # 5. Zones Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        required_level INTEGER DEFAULT 1
    )
    ''')

    # 6. Bosses Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bosses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        hp INTEGER NOT NULL,
        attack INTEGER NOT NULL,
        zone_id INTEGER NOT NULL,
        required_level INTEGER DEFAULT 1,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (zone_id) REFERENCES zones(id)
    )
    ''')

    # 7. Territories Table (Owned by a Character)
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

    # 8. NPCs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS npcs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        zone TEXT NOT NULL,
        dialogue_prompt TEXT
    )
    ''')

    # 9. Quests Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL UNIQUE,
        description TEXT,
        npc_id INTEGER NOT NULL,
        required_level INTEGER DEFAULT 1,
        reward_xp INTEGER DEFAULT 0,
        reward_luxium INTEGER DEFAULT 0,
        FOREIGN KEY (npc_id) REFERENCES npcs(id)
    )
    ''')

    # 10. Character-Quests Linking Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS character_quests (
        character_id INTEGER NOT NULL,
        quest_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('proposée', 'active', 'terminée')),
        PRIMARY KEY (character_id, quest_id),
        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
        FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
    )
    ''')

    # 11. Artefacts Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artefacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        rarity TEXT NOT NULL CHECK(rarity IN ('Commun', 'Rare', 'Légendaire', 'Unique'))
    )
    ''')

    # 12. Character-Artefacts Linking Table (Inventory)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS character_artefacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER NOT NULL,
        artefact_id INTEGER NOT NULL,
        FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
        FOREIGN KEY (artefact_id) REFERENCES artefacts(id) ON DELETE CASCADE
    )
    ''')

    # 13. World Events Table
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

    # Populate Artefacts with sample data
    artefacts = [
        ('Fragment de lune', 'Un éclat de la lune, froid au toucher.', 'Commun'),
        ('Orbe de vision', 'Permet de voir des fragments du futur.', 'Rare'),
        ('Lame du chaos', 'Une arme forgée dans le feu du chaos primordial.', 'Légendaire')
    ]
    cursor.executemany("INSERT INTO artefacts (name, description, rarity) VALUES (?, ?, ?)", artefacts)

    # Populate Zones
    zones = [
        ('Clairière des Murmures', 'Une clairière paisible où les nouveaux aventuriers commencent leur voyage. La magie y est douce.', 1),
        ('Forêt des Ombres', 'Une forêt dense et sombre, peuplée de créatures mystérieuses. On dit que les arbres chuchotent des secrets anciens.', 5)
    ]
    cursor.executemany("INSERT INTO zones (name, description, required_level) VALUES (?, ?, ?)", zones)

    # Populate Bosses
    # Zone ID for "Forêt des Ombres" is 2
    cursor.execute(
        "INSERT INTO bosses (name, description, hp, attack, zone_id, required_level) VALUES (?, ?, ?, ?, ?, ?)",
        (
            'Gardien Sombre',
            'Une créature massive de bois et d\'ombre, protégeant les secrets les plus profonds de la forêt.',
            500,
            40,
            2, # Forêt des Ombres
            10
        )
    )

    # Populate NPCs
    cursor.execute(
        "INSERT INTO npcs (name, description, zone, dialogue_prompt) VALUES (?, ?, ?, ?)",
        (
            'Elara',
            'Une mystérieuse gardienne du savoir ancien, ses yeux brillent d\'une lueur sage.',
            'Clairière des Murmures',
            'Salutations, voyageur. Le vent m\'a parlé de votre venue. Que cherchez-vous en ces terres ancestrales ?'
        )
    )
    # Get Elara's ID for the quest
    elara_id = cursor.lastrowid

    # Populate Quests
    cursor.execute(
        "INSERT INTO quests (title, description, npc_id, required_level, reward_xp, reward_luxium) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "L'Aube d'un Aventurier",
            "Faites vos premiers pas à Zilantia. Parlez à Elara pour comprendre votre destinée et recevoir votre première mission.",
            elara_id,
            1,
            50,
            10
        )
    )


    conn.commit()
    conn.close()
    print("Database `zilantia.db` has been set up for Zilantia.")

if __name__ == '__main__':
    setup_database()
