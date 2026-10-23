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
            connection.execute(
                """
                DELETE FROM documents
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM documents
                    GROUP BY text
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_text
                ON documents (text)
                """
            )
            connection.commit()

    def delete_document_by_id(self, document_id: int) -> int:
        """Delete a saved fact by ID; return the number of rows deleted."""
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
            connection.commit()
            return cursor.rowcount
                
    def list_documents(self) -> list[tuple[int, str]]:
        """Return saved facts as (id, text), ordered by ID."""
        with closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(
                "SELECT id, text FROM documents ORDER BY id"
            ).fetchall()

        return [(document_id, text) for document_id, text in rows]

    
    def add_document(self, text: str) -> None:
        embedding = self.embedding_model.embed(text)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO documents (text, embedding) VALUES (?, ?)",
                (text, json.dumps(embedding)),
            )
            connection.commit()

    def search(
        self, query: str, limit: int = 3, min_similarity: float = 0.5
    ) -> list[str]:
        """Return relevant document text above the similarity threshold."""
        return [
            text
            for _, text in self.search_with_scores(
                query, limit, min_similarity
            )
        ]

    def search_with_scores(
        self,
        query: str,
        limit: int = 3,
        min_similarity: float = 0.5,
    ) -> list[tuple[float, str]]:
        """Return relevant documents with cosine similarity scores."""
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
        ranked = [
            (score, text)
            for score, text in ranked
            if score >= min_similarity
        ]
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[:limit]

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