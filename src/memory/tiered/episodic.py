"""Episodic memory: summarised chunks in SQLite FTS5, retrieved by keyword."""
import re
import sqlite3

STOPWORDS = {"a", "an", "and", "are", "at", "by", "can", "day", "do", "for", "how", "i", "in", "is", "it", "many", "me",
             "my", "of", "on", "our", "the", "to", "try", "was", "what", "when", "where", "which", "who", "you"}


def fts_query(text: str) -> str:
    """Quote every keyword, so user text can never be parsed as FTS5 syntax."""
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    return " OR ".join(f'"{word}"' for word in words)


class EpisodicMemory:
    def __init__(self, cap: int, decay: float, db_path: str = ":memory:"):
        self.cap = cap
        self.decay = decay
        self.db = sqlite3.connect(db_path)
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS episodes USING fts5(text, importance UNINDEXED, turn UNINDEXED)")

    def add(self, text: str, importance: float, turn: int) -> None:
        self.db.execute("INSERT INTO episodes(text, importance, turn) VALUES (?, ?, ?)", (text, importance, turn))
        self._evict(turn)

    def _evict(self, now: int) -> None:
        rows = self.db.execute("SELECT rowid, importance, turn FROM episodes").fetchall()
        rows.sort(key=lambda row: float(row[1]) * self.decay ** (now - int(row[2])))
        for rowid, _, _ in rows[:max(0, len(rows) - self.cap)]:
            self.db.execute("DELETE FROM episodes WHERE rowid = ?", (rowid,))

    def search(self, text: str, top_k: int) -> list[str]:
        query = fts_query(text)
        if not query:
            return []
        rows = self.db.execute("SELECT text FROM episodes WHERE episodes MATCH ? ORDER BY bm25(episodes) LIMIT ?",
                               (query, top_k)).fetchall()
        return [row[0] for row in rows]

    def count(self) -> int:
        return self.db.execute("SELECT count(*) FROM episodes").fetchone()[0]
