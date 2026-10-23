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


def test_search_with_scores_ranks_by_similarity(tmp_path):
    class FixedEmbeddingModel:
        def embed(self, text: str) -> list[float]:
            vectors = {
                "query": [1.0, 0.0],
                "aligned fact": [1.0, 0.0],
                "unrelated fact": [0.0, 1.0],
                "no match query": [-1.0, 0.0],
            }
            return vectors[text]

    retriever = DocumentRetriever(
        FixedEmbeddingModel(),
        str(tmp_path / "retrieval.sqlite3"),
    )
    retriever.add_document("unrelated fact")
    retriever.add_document("aligned fact")

    assert retriever.search_with_scores("query") == [
        (1.0, "aligned fact"),
    ]
    assert retriever.search("no match query") == []


def test_adding_duplicate_fact_returns_one_match(tmp_path):
    retriever = DocumentRetriever(
        FakeEmbeddingModel(),
        str(tmp_path / "retrieval.sqlite3"),
    )
    fact = "My preferred name is Ada."

    retriever.add_document(fact)
    retriever.add_document(fact)

    assert retriever.search(fact) == [fact]


def test_list_documents_returns_ids_and_text(tmp_path):
    retriever = DocumentRetriever(
        FakeEmbeddingModel(),
        str(tmp_path / "retrieval.sqlite3"),
    )
    fact = "My preferred name is Ada."
    retriever.add_document(fact)

    documents = retriever.list_documents()

    assert len(documents) == 1
    document_id, text = documents[0]
    assert document_id > 0
    assert text == fact



def test_delete_document_by_id(tmp_path):
    retriever = DocumentRetriever(
        FakeEmbeddingModel(),
        str(tmp_path / "retrieval.sqlite3"),
    )
    retriever.add_document("My preferred name is Ada.")
    document_id, _ = retriever.list_documents()[0]

    assert retriever.delete_document_by_id(document_id) == 1
    assert retriever.delete_document_by_id(document_id) == 0
    assert retriever.list_documents() == []