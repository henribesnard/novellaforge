"""RAG service for indexing and retrieving project context."""
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncio
import logging
import warnings

try:
    from qdrant_client import QdrantClient as _QdrantClient
    from qdrant_client.http import models as _qdrant_models
    _QDRANT_AVAILABLE = True
    _QDRANT_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - defensive import
    _QDRANT_AVAILABLE = False
    _QDRANT_IMPORT_ERROR = exc
    _QdrantClient = None
    _qdrant_models = None

try:
    from langchain_qdrant import Qdrant as _Qdrant
    from langchain_huggingface import HuggingFaceEmbeddings as _HuggingFaceEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter as _RecursiveCharacterTextSplitter
    _RAG_DEPS_AVAILABLE = True
    _RAG_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - defensive import
    _RAG_DEPS_AVAILABLE = False
    _RAG_IMPORT_ERROR = exc
    _Qdrant = None
    _HuggingFaceEmbeddings = None
    _RecursiveCharacterTextSplitter = None

from app.core.config import settings
from app.models.document import Document


logger = logging.getLogger(__name__)


class RagService:
    """Index project documents into Qdrant and retrieve relevant chunks."""

    def __init__(self) -> None:
        self.enabled = _QDRANT_AVAILABLE and _RAG_DEPS_AVAILABLE
        self.disabled_reason: Optional[str] = None
        self._logged_disabled = False
        if not self.enabled:
            reasons: List[str] = []
            if not _QDRANT_AVAILABLE:
                reasons.append(f"qdrant_client unavailable: {_QDRANT_IMPORT_ERROR}")
            if not _RAG_DEPS_AVAILABLE:
                reasons.append(f"langchain deps unavailable: {_RAG_IMPORT_ERROR}")
            self.disabled_reason = "; ".join(reasons)
            self.client = None
            self.collection_name = settings.QDRANT_COLLECTION_NAME
            self.embeddings = None
            self.text_splitter = None
            logger.warning("RAG disabled: %s", self.disabled_reason)
            return

        if (
            settings.DEBUG
            and settings.QDRANT_API_KEY
            and settings.QDRANT_URL.startswith("http://")
        ):
            warnings.filterwarnings(
                "ignore",
                message="Api key is used with an insecure connection",
            )
        self.client = _QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.embeddings = _HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.text_splitter = _RecursiveCharacterTextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )

    def _check_enabled(self, action: str) -> bool:
        if not self.enabled:
            if not self._logged_disabled:
                logger.warning("RAG disabled, skipping %s. Reason: %s", action, self.disabled_reason)
                self._logged_disabled = True
            return False
        return True

    def _build_vector_store(self):
        """Create a Qdrant vector store instance with compatibility fallback."""
        try:
            return _Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )
        except TypeError:
            return _Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embedding=self.embeddings,
            )

    async def warmup(self) -> None:
        """Preload embedding model weights to reduce first-call latency."""
        try:
            await asyncio.to_thread(self.embeddings.embed_query, "warmup")
        except Exception:
            logger.exception("RAG warmup failed")

    def _ensure_collection(self) -> None:
        """Ensure the Qdrant collection exists."""
        if not self._check_enabled("_ensure_collection"):
            return
        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=_qdrant_models.VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=_qdrant_models.Distance.COSINE,
            ),
        )

    def _delete_project_vectors(self, project_id: UUID) -> None:
        """Delete existing vectors for a project to avoid duplicates."""
        if not self._check_enabled("_delete_project_vectors"):
            return
        project_filter = _qdrant_models.Filter(
            must=[
                _qdrant_models.FieldCondition(
                    key="project_id",
                    match=_qdrant_models.MatchValue(value=str(project_id)),
                )
            ]
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=project_filter,
        )

    def _delete_document_vectors(self, project_id: UUID, document_id: UUID) -> None:
        """Delete existing vectors for a single document."""
        if not self._check_enabled("_delete_document_vectors"):
            return
        document_filter = _qdrant_models.Filter(
            must=[
                _qdrant_models.FieldCondition(
                    key="project_id",
                    match=_qdrant_models.MatchValue(value=str(project_id)),
                ),
                _qdrant_models.FieldCondition(
                    key="document_id",
                    match=_qdrant_models.MatchValue(value=str(document_id)),
                ),
            ]
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=document_filter,
        )

    def index_documents(
        self,
        project_id: UUID,
        documents: List[Document],
        clear_existing: bool = True,
    ) -> int:
        """Split and index documents into Qdrant. Returns number of chunks."""
        if not self._check_enabled("index_documents"):
            return 0
        self._ensure_collection()

        if clear_existing:
            self._delete_project_vectors(project_id)

        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for doc in documents:
            if not doc.content:
                continue
            chunks = self.text_splitter.split_text(doc.content)
            for idx, chunk in enumerate(chunks):
                texts.append(chunk)
                metadatas.append(
                    {
                        "project_id": str(project_id),
                        "document_id": str(doc.id),
                        "title": doc.title,
                        "order_index": doc.order_index,
                        "document_type": doc.document_type.value if doc.document_type else None,
                        "chunk_index": idx,
                    }
                )

        if not texts:
            return 0

        vector_store = self._build_vector_store()
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        return len(texts)

    def update_document(self, project_id: UUID, document: Document) -> int:
        """Update vectors for a single document."""
        if not self._check_enabled("update_document"):
            return 0
        self._ensure_collection()
        self._delete_document_vectors(project_id, document.id)
        if not document.content:
            return 0

        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        chunks = self.text_splitter.split_text(document.content)
        for idx, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append(
                {
                    "project_id": str(project_id),
                    "document_id": str(document.id),
                    "title": document.title,
                    "order_index": document.order_index,
                    "document_type": document.document_type.value if document.document_type else None,
                    "chunk_index": idx,
                }
            )

        if not texts:
            return 0

        vector_store = self._build_vector_store()
        vector_store.add_texts(texts=texts, metadatas=metadatas)
        return len(texts)

    def retrieve(
        self,
        project_id: UUID,
        query: str,
        top_k: int,
    ) -> List[str]:
        """Retrieve top-k relevant chunks for a project."""
        if not self._check_enabled("retrieve"):
            return []
        self._ensure_collection()
        vector_store = self._build_vector_store()
        project_filter = _qdrant_models.Filter(
            must=[
                _qdrant_models.FieldCondition(
                    key="project_id",
                    match=_qdrant_models.MatchValue(value=str(project_id)),
                )
            ]
        )
        docs = vector_store.similarity_search(query, k=top_k, filter=project_filter)
        return [doc.page_content for doc in docs]

    def count_project_vectors(self, project_id: UUID) -> int:
        """Count vectors for a project."""
        if not self._check_enabled("count_project_vectors"):
            return 0
        self._ensure_collection()
        project_filter = _qdrant_models.Filter(
            must=[
                _qdrant_models.FieldCondition(
                    key="project_id",
                    match=_qdrant_models.MatchValue(value=str(project_id)),
                )
            ]
        )
        count_result = self.client.count(
            collection_name=self.collection_name,
            count_filter=project_filter,
            exact=True,
        )
        return int(count_result.count or 0)

    async def aindex_documents(
        self,
        project_id: UUID,
        documents: List[Document],
        clear_existing: bool = True,
    ) -> int:
        """Async wrapper for indexing documents."""
        return await asyncio.to_thread(self.index_documents, project_id, documents, clear_existing)

    async def aupdate_document(self, project_id: UUID, document: Document) -> int:
        """Async wrapper for updating a single document."""
        return await asyncio.to_thread(self.update_document, project_id, document)

    async def aretrieve(
        self,
        project_id: UUID,
        query: str,
        top_k: int,
    ) -> List[str]:
        """Async wrapper for retrieval."""
        return await asyncio.to_thread(self.retrieve, project_id, query, top_k)

    async def acount_project_vectors(self, project_id: UUID) -> int:
        """Async wrapper for vector count."""
        return await asyncio.to_thread(self.count_project_vectors, project_id)
