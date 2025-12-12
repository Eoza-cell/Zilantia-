import sqlite3

def setup_database():
    """
    Sets up the SQLite database, creating tables for the Zilantia world.
    This function should be run once to initialize the database.
    """
    conn = sqlite3.connect('zilantia.db')
    cursor = conn.cursor()

    # --- Create Tables ---

    # Players Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        user_name TEXT NOT NULL,
        user_avatar_url TEXT,
        race TEXT,
        pouvoir TEXT,
        niveau INTEGER DEFAULT 1,
        health INTEGER DEFAULT 100,
        traits_uniques TEXT DEFAULT 'Aucun pour le moment.',
        artefact TEXT DEFAULT 'Aucun pour le moment.',
        location_key TEXT,
        FOREIGN KEY (location_key) REFERENCES locations(key)
    )
    ''')

    # Player Missions (Junction Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_missions (
        player_user_id INTEGER,
        mission_id TEXT,
        status TEXT, -- e.g., 'accepted', 'completed'
        progress TEXT, -- JSON string for complex progress
        PRIMARY KEY (player_user_id, mission_id),
        FOREIGN KEY (player_user_id) REFERENCES players(user_id),
        FOREIGN KEY (mission_id) REFERENCES missions(id)
    )
    ''')

    # Locations Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        key TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        channel_id INTEGER
    )
    ''')

    # PNJ Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pnjs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        system_prompt TEXT,
        location_key TEXT,
        FOREIGN KEY (location_key) REFERENCES locations(key)
    )
    ''')

    # Items Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        location_key TEXT,
        FOREIGN KEY (location_key) REFERENCES locations(key)
    )
    ''')

    # Enemies Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enemies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        health INTEGER,
        damage INTEGER,
        location_key TEXT,
        FOREIGN KEY (location_key) REFERENCES locations(key)
    )
    ''')

    # Missions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS missions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        start_objective TEXT, -- e.g., {"action": "interact", "target": "Colis suspect"}
        end_objective TEXT,
        reward TEXT,
        start_location_key TEXT,
        FOREIGN KEY (start_location_key) REFERENCES locations(key)
    )
    ''')

    # Active Combats Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_combats (
        player_user_id INTEGER PRIMARY KEY,
        enemy_id INTEGER NOT NULL,
        enemy_current_health INTEGER NOT NULL,
        FOREIGN KEY (player_user_id) REFERENCES players(user_id),
        FOREIGN KEY (enemy_id) REFERENCES enemies(id)
    )
    ''')

    # Location Exits Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS location_exits (
        source_location_key TEXT,
        direction TEXT,
        destination_location_key TEXT,
        PRIMARY KEY (source_location_key, direction),
        FOREIGN KEY (source_location_key) REFERENCES locations(key),
        FOREIGN KEY (destination_location_key) REFERENCES locations(key)
    )
    ''')

    # --- Initial Data Insertion ---

    # Locations
    locations_data = [
        ('quartier_pauvre', 'Quartier Pauvre', "Un dédale de ruelles humides et de bâtiments délabrés. L'odeur de la pauvreté et du désespoir est palpable.", None),
        ('port', 'Le Port de Zilantia', "Des grues rouillées se dressent vers le ciel. Les conteneurs sont une cachette parfaite pour les trafics.", None),
        ('manoir_varlox', "Manoir de Varlox", "Une immense bâtisse sombre qui surplombe la ville. Les ombres semblent danser sur ses murs.", None)
    ]
    cursor.executemany('INSERT OR IGNORE INTO locations (key, name, description, channel_id) VALUES (?, ?, ?, ?)', locations_data)

    # PNJs
    pnjs_data = [
        ('Vieux Leo', 'Un vieil homme assis sur un carton, il a tout vu.', "Tu es Leo, un vieil homme fatigué qui a vu la cruauté de la rue. Tu parles avec des phrases courtes et méfiantes.", 'quartier_pauvre'),
        ("Contact de l'Ombre", "Un homme au visage dissimulé.", "Tu es un contact du Syndicat Noir. Tu es professionnel, direct et tu ne donnes aucune information superflue. Tu ne parles que de la mission en cours.", 'port'),
        ('Don Varlox', "Le Roi des Ombres, assis sur un trône d'obsidienne.", "Tu es Don Varlox, le chef impitoyable du Syndicat Noir. Tu es arrogant, tu parles avec supériorité et tu vois les autres comme des pions. Tes phrases sont menaçantes et calculatrices.", 'manoir_varlox')
    ]
    cursor.executemany('INSERT OR IGNORE INTO pnjs (name, description, system_prompt, location_key) VALUES (?, ?, ?, ?)', pnjs_data)

    # Items
    items_data = [
        ('Colis suspect', 'Une caisse en bois qui vibre légèrement. Prêt pour la mission `Livraison Sombre`?', 'quartier_pauvre')
    ]
    cursor.executemany('INSERT OR IGNORE INTO items (name, description, location_key) VALUES (?, ?, ?)', items_data)

    # Enemies
    enemies_data = [
        ('Homme de main du Syndicat', 40, 8, 'port')
    ]
    cursor.executemany('INSERT OR IGNORE INTO enemies (name, health, damage, location_key) VALUES (?, ?, ?, ?)', enemies_data)

    # Missions
    missions_data = [
        ('livraison_sombre', 'Livraison Sombre', 'Transporter une caisse qui bouge toute seule du quartier pauvre au port.', '{"action": "interact", "target": "Colis suspect"}', '{"action": "interact", "target": "Contact de l\'Ombre"}', '{"cash": 500}', 'quartier_pauvre'),
        ('nettoyage_rue', 'Nettoyage de Rue', 'Éliminer un petit gang qui refuse de payer Varlox dans le quartier pauvre.', '{"action": "defeat", "target": "Chef de gang rival"}', None, '{"cash": 1000, "reputation": 10}', 'quartier_pauvre'),
        ('crash_port', 'Crash sur le Port', 'Récupérer un conteneur d’artefacts sur le port avant la police.', '{"action": "interact", "target": "Conteneur"}', None, '{"item": "Artefact instable"}', 'port'),
        ('ombre_toit', 'Ombre sur le Toit', 'Espionner un politicien véreux pour Varlox.', '{"action": "scan", "target_location": "hotel_luxe"}', None, '{"cash": 750}', 'manoir_varlox'),
        ('fuite_nocturne', 'La Fuite en Nocturne', 'Échapper à une poursuite de la police après un deal qui a mal tourné.', '{"action": "move", "from": "port", "to": "quartier_pauvre"}', None, '{"reputation": 15}', 'port'),
        ('tueur_ombre', 'Le Tueur d’Ombre', 'Survivre à une embuscade d’un assassin aux pouvoirs similaires à ceux de Varlox.', '{"action": "defeat", "target": "Tueur d\'Ombre"}', None, '{"pouvoir_up": 1}', 'quartier_pauvre'),
        ('voleurs_artefacts', 'Les Voleurs d’Artefacts', 'Défendre un laboratoire secret du Syndicat contre des rivaux.', '{"action": "defend", "location": "labo_secret"}', None, '{"cash": 1500}', 'manoir_varlox'),
        ('explosion_tunnel', 'Explosion au Tunnel Nord', 'Désamorcer une bombe magique posée par un gang rival sous la ville.', '{"action": "interact", "target": "Bombe magique"}', None, '{"reputation": 25, "cash": 500}', 'manoir_varlox')
    ]
    cursor.executemany('INSERT OR IGNORE INTO missions (id, name, description, start_objective, end_objective, reward, start_location_key) VALUES (?, ?, ?, ?, ?, ?, ?)', missions_data)

    # Location Exits
    exits_data = [
        ('quartier_pauvre', 'nord', 'port'),
        ('port', 'sud', 'quartier_pauvre'),
        ('port', 'est', 'manoir_varlox'),
        ('manoir_varlox', 'ouest', 'port')
    ]
    cursor.executemany('INSERT OR IGNORE INTO location_exits (source_location_key, direction, destination_location_key) VALUES (?, ?, ?)', exits_data)


    conn.commit()
    conn.close()
    print("Database `zilantia.db` has been set up successfully.")

if __name__ == '__main__':
    setup_database()
