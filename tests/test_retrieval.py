from SPROUT.memory.retrieval import DocumentRetriever


class FakeEmbeddingModel:
    def embed(self, text: str) -> list[float]:
        return [float(len(text)), float(sum(map(ord, text)) % 997)]


def test_new_retriever_reads_saved_document(tmp_path):
    database = str(tmp_path / "retrieval.sqlite3")
    document = "A saved memory record."

    first = DocumentRetriever(FakeEmbeddingModel(), database)
    first.add_document(document)

    second = DocumentRetriever(FakeEmbeddingModel(), database)

    assert second.search("memory record", limit=1) == [document]


def test_delete_document_removes_saved_document(tmp_path):
    database = str(tmp_path / "retrieval.sqlite3")
    document = "A saved memory record."
    retriever = DocumentRetriever(FakeEmbeddingModel(), database)
    retriever.add_document(document)

    assert retriever.delete_document(document) == 1

    reopened = DocumentRetriever(FakeEmbeddingModel(), database)
    assert reopened.search("memory record") == []