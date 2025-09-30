# league_drafts.py

import sqlite3
from typing import List, Dict, Any, Optional

DB_FILE = "ff_app.db"


def create_table() -> None:
    """Create the league_drafts table if it does not exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_drafts (
                draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                round INTEGER NOT NULL,
                pick_number INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                position TEXT,
                team TEXT,
                UNIQUE (league_id, round, pick_number),
                FOREIGN KEY (league_id) REFERENCES leagues(league_id),
                FOREIGN KEY (member_id) REFERENCES members(member_id)
            )
        """)
        conn.commit()


def add_draft_pick(
    league_id: int,
    round: int,
    pick_number: int,
    member_id: int,
    player_name: str,
    position: Optional[str] = None,
    team: Optional[str] = None
) -> int:
    """Insert or replace a draft pick for a given league, round, and pick number."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO league_drafts 
                (league_id, round, pick_number, member_id, player_name, position, team)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (league_id, round, pick_number, member_id, player_name, position, team))
        conn.commit()
        return cursor.lastrowid


def get_draft_by_league(league_id: int) -> List[Dict[str, Any]]:
    """Fetch all draft picks for a league ordered by round and pick number."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT draft_id, league_id, round, pick_number, member_id, player_name, position, team
            FROM league_drafts
            WHERE league_id = ?
            ORDER BY round ASC, pick_number ASC
        """, (league_id,))
        rows = cursor.fetchall()

    return [
        {
            "draft_id": row[0],
            "league_id": row[1],
            "round": row[2],
            "pick_number": row[3],
            "member_id": row[4],
            "player_name": row[5],
            "position": row[6],
            "team": row[7],
        }
        for row in rows
    ]


def delete_draft_pick(draft_id: int) -> None:
    """Delete a specific draft pick by draft_id."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM league_drafts WHERE draft_id = ?", (draft_id,))
        conn.commit()


if __name__ == "__main__":
    # Run this file directly to set up the table
    create_table()
    print("✅ league_drafts table created successfully.")
