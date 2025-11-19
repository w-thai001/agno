"""Search Indexer FSA with document indexing and query matching."""
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Set, Tuple


class IndexState(Enum):
    """FSA States for search indexing."""
    IDLE, INDEXING, INDEXED, QUERYING = "idle", "indexing", "indexed", "querying"


class SearchIndexer:
    """Finite State Automaton for search indexing and query matching."""

    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive
        self.index: Dict[str, Set[str]] = defaultdict(set)
        self.documents: Dict[str, Any] = {}
        self.state = IndexState.IDLE

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into searchable terms."""
        text = text if self.case_sensitive else text.lower()
        return [word.strip('.,!?;:"()[]{}') for word in text.split() if word.strip('.,!?;:"()[]{}')]

    def index_document(self, doc_id: str, content: str, metadata: Any = None) -> None:
        """Index a document for searching."""
        self.state = IndexState.INDEXING
        self.documents[doc_id] = {"content": content, "metadata": metadata}
        for token in self._tokenize(content):
            self.index[token].add(doc_id)
        self.state = IndexState.INDEXED

    def index_batch(self, documents: List[Tuple[str, str, Any]]) -> None:
        """Index multiple documents at once."""
        self.state = IndexState.INDEXING
        for doc_id, content, metadata in documents:
            self.documents[doc_id] = {"content": content, "metadata": metadata}
            for token in self._tokenize(content):
                self.index[token].add(doc_id)
        self.state = IndexState.INDEXED

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents matching query."""
        if self.state == IndexState.IDLE:
            return []
        self.state = IndexState.QUERYING
        doc_scores: Dict[str, int] = defaultdict(int)
        for token in self._tokenize(query):
            for doc_id in self.index.get(token, set()):
                doc_scores[doc_id] += 1
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        results = [{"doc_id": doc_id, "score": score, **self.documents[doc_id]} for doc_id, score in sorted_docs]
        self.state = IndexState.INDEXED
        return results

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        if doc_id not in self.documents:
            return False
        content = self.documents[doc_id]["content"]
        tokens = self._tokenize(content)
        for token in tokens:
            self.index[token].discard(doc_id)
            if not self.index[token]:
                del self.index[token]
        del self.documents[doc_id]
        self.state = IndexState.INDEXED if self.documents else IndexState.IDLE
        return True

    def clear(self) -> None:
        """Clear all indexed documents."""
        self.index.clear()
        self.documents.clear()
        self.state = IndexState.IDLE
