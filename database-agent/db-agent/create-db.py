import os 
import sqlite3
import sys
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "life_tracker.db")

def create_db():
    db_exists = os.path.exists(DATABASE_PATH)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if db_exists:
        print(f"Database file already exists at {DATABASE_PATH}. No changes made")
        sys.exit(0)

    try:

        print(f"Creating new database at {DATABASE_PATH}...")
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
        """)
        print("✅ Users table created successfully")

        # Expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date DATE NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
        print("✅ Expenses table created successfully")

        # Workouts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                calories_burned INTEGER NOT NULL,
                date DATE NOT NULL,
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
        print("✅ Workouts table created successfully")

        # Habits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                frequency TEXT NOT NULL,
                target INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
        print("✅ Habits table created successfully")

        # habit_logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status INTEGER NOT NULL,  -- 1 = completed, 0 = skipped
                notes TEXT,
                FOREIGN KEY (habit_id) REFERENCES habits(id)
            )
            """
        )
        print("✅ habit_logs table created successfully")

        # Insert dummy users
        now = datetime.now().isoformat(sep=' ', timespec='seconds')
        dummy_users = [
            ("aiman", "aiman@gmail.com", now),
            ("steven", "steven@gmail.com", "2025-01-01 12:00:00"),
            ("alara", "alara@gmail.com", "2025-05-27 16:42:30"),
        ]

        cursor.executemany("INSERT INTO users (username, email, created_at) VALUES (?, ?, ?)", dummy_users)
        print("👤 Dummy users inserted successfully")

        conn.commit()

    except Exception as e:
        print(f"❌ Error creating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_db()