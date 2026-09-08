from datetime import date

from fastapi.testclient import TestClient

from legal_matter_service import MatterIntake, app, get_index
from legal_retrieval import RetrievedPassage


class FixedIndex:
    def answer_passages(self, matter_id: str, question: str, top_k: int = 3) -> list[RetrievedPassage]:
        assert matter_id == "MAT-1042"
        assert "deadline" in question
        return [
            RetrievedPassage(
                document_id="engagement-letter-2026",
                title="Signed engagement letter",
                text="The response deadline is 17 September 2026.",
            )
        ]


def test_missing_signed_delivery_takes_priority_over_deadline() -> None:
    matter = MatterIntake(
        matter_id="MAT-1042",
        client_name="Northwind Legal",
        signed_document_delivered_at=None,
        next_deadline=date(2026, 9, 17),
    )
    assert matter.signed_document_delivered_at is None

    app.dependency_overrides[get_index] = lambda: FixedIndex()
    try:
        response = TestClient(app).post(
            "/matter-answers",
            json={
                "matter": matter.model_dump(mode="json"),
                "question": "What is the response deadline?",
                "as_of": "2026-09-01",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "matter_id": "MAT-1042",
        "answer": "The response deadline is 17 September 2026.",
        "citations": [
            {"document_id": "engagement-letter-2026", "title": "Signed engagement letter"}
        ],
        "follow_up": "deliver_signed_document",
    }
