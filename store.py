import sqlite3
import json
import os

class MultiModelStore:
    def __init__(self, db_path="harness_data.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    repo TEXT,
                    size_gb REAL,
                    vram_fit TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    model_name TEXT,
                    gen_speed_ts REAL,
                    total_tokens INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hardware_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    action TEXT,
                    status TEXT
                )
            """)
            conn.commit()

    def get_all(self, table_name):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            return [dict(row) for row in cursor.fetchall()]

    def insert_metric(self, timestamp, model_name, gen_speed_ts, total_tokens):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO performance_metrics (timestamp, model_name, gen_speed_ts, total_tokens) VALUES (?, ?, ?, ?)",
                (timestamp, model_name, gen_speed_ts, total_tokens)
            )
            conn.commit()
