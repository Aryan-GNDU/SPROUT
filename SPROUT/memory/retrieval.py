import json
import sqlite3
from contextlib import closing
from pathlib import Path

from SPROUT.core.llm import EmbeddingModel


class DocumentRetriever:
    """Persist documents and retrieve the most relevant ones."""

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        db_path: str = "sprout_memory.sqlite3",
    ):
        self.embedding_model = embedding_model
        self.db_path = Path(db_path)

        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def add_document(self, text: str) -> None:
        embedding = self.embedding_model.embed(text)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                "INSERT INTO documents (text, embedding) VALUES (?, ?)",
                (text, json.dumps(embedding)),
            )
            connection.commit()

    def search(self, query: str, limit: int = 3) -> list[str]:
        if limit <= 0:
            return []

        query_embedding = self.embedding_model.embed(query)
        with closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(
                "SELECT text, embedding FROM documents"
            ).fetchall()

        ranked = [
            (self._cosine(query_embedding, json.loads(embedding)), text)
            for text, embedding in rows
        ]
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in ranked[:limit]]

    def delete_document(self, text: str) -> int:
        """Delete all documents whose text exactly matches; return count."""
        if not text.strip():
            return 0

        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE text = ?",
                (text,),
            )
            connection.commit()
            return cursor.rowcount
        

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sum(value * value for value in left) ** 0.5
        right_norm = sum(value * value for value in right) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)