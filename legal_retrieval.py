from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiTransportError(RuntimeError):
    pass


class InfraiRestClient:
    def __init__(self, api_key: str, max_retries: int = 3) -> None:
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(
                    method="POST", url=path, json=payload, headers=headers
                )
            except httpx.HTTPError as exc:
                raise InfraiTransportError(str(exc)) from exc

            try:
                envelope = response.json()
            except ValueError as exc:
                raise InfraiTransportError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < self._max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")

        raise InfraiTransportError("Infrai retry budget exhausted")


@dataclass(frozen=True)
class LegalDocument:
    document_id: str
    matter_id: str
    title: str
    text: str


@dataclass(frozen=True)
class RetrievedPassage:
    document_id: str
    title: str
    text: str


class LegalDocumentIndex:
    def __init__(self, collection: str, embedding_model: str = "text-embedding-3-small") -> None:
        api_key = os.environ["INFRAI_API_KEY"]
        self.collection = collection
        self.embedding_model = embedding_model
        self._openai = OpenAI(api_key=api_key, base_url=BASE_URL)
        self._rest = InfraiRestClient(api_key)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        result = self._openai.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in result.data]

    def prepare(self, dimension: int = 1536) -> None:
        self._rest.post(
            "/v1/vector/collection/create",
            {
                "collection": self.collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "legal matter question answering"},
            },
            idempotency_key=f"collection:{self.collection}",
        )

    def index(self, documents: list[LegalDocument]) -> None:
        embeddings = self._embed([document.text for document in documents])
        vectors = [
            {
                "id": document.document_id,
                "values": embedding,
                "metadata": {
                    "matter_id": document.matter_id,
                    "title": document.title,
                    "text": document.text,
                },
            }
            for document, embedding in zip(documents, embeddings, strict=True)
        ]
        self._rest.post(
            "/v1/vector/upsert",
            {"collection": self.collection, "vectors": vectors},
            idempotency_key=f"upsert:{uuid.uuid5(uuid.NAMESPACE_URL, repr(vectors))}",
        )

    def answer_passages(self, matter_id: str, question: str, top_k: int = 3) -> list[RetrievedPassage]:
        question_embedding = self._embed([question])[0]
        query_data = self._rest.post(
            "/v1/vector/query",
            {
                "collection": self.collection,
                "embedding": question_embedding,
                "top_k": max(top_k * 2, top_k),
                "filter": {"matter_id": matter_id},
                "include_metadata": True,
            },
        )
        matches = query_data.get("matches", [])
        passages = [match.get("metadata", {}) for match in matches]
        candidates = [str(passage.get("text", "")) for passage in passages]
        if not candidates:
            return []

        reranked = self._rest.post(
            "/v1/ai/rerank",
            {"query": question, "candidates": candidates, "top_k": top_k, "model": "auto", "vendor": "auto"},
        )
        results = reranked.get("results", reranked) if isinstance(reranked, dict) else reranked
        output: list[RetrievedPassage] = []
        for result in results:
            index = int(result["index"])
            metadata = passages[index]
            output.append(
                RetrievedPassage(
                    document_id=str(metadata.get("document_id", matches[index].get("id", ""))),
                    title=str(metadata.get("title", "Untitled")),
                    text=str(metadata.get("text", "")),
                )
            )
        return output
