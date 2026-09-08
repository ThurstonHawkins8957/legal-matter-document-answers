from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from legal_retrieval import InfraiError, LegalDocumentIndex


class MatterIntake(BaseModel):
    matter_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    signed_document_delivered_at: datetime | None = None
    next_deadline: date


class MatterQuestion(BaseModel):
    matter: MatterIntake
    question: str = Field(min_length=3)
    top_k: Annotated[int, Field(ge=1, le=10)] = 3
    as_of: date = Field(default_factory=date.today)


class Citation(BaseModel):
    document_id: str
    title: str


class MatterAnswer(BaseModel):
    matter_id: str
    answer: str
    citations: list[Citation]
    follow_up: Literal["deliver_signed_document", "deadline_due", "none"]


def decide_follow_up(matter: MatterIntake, as_of: date) -> Literal["deliver_signed_document", "deadline_due", "none"]:
    if matter.signed_document_delivered_at is None:
        return "deliver_signed_document"
    if matter.next_deadline <= as_of:
        return "deadline_due"
    return "none"


@lru_cache
def get_index() -> LegalDocumentIndex:
    return LegalDocumentIndex(collection="legal-matter-documents")


app = FastAPI(title="Legal matter document answers")


@app.post("/matter-answers", response_model=MatterAnswer)
def answer_matter_question(
    request: MatterQuestion,
    index: LegalDocumentIndex = Depends(get_index),
) -> MatterAnswer:
    try:
        passages = index.answer_passages(request.matter.matter_id, request.question, request.top_k)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail={"code": exc.code, "message": str(exc)}) from exc

    answer = passages[0].text if passages else "No matching passage was found in this matter."
    return MatterAnswer(
        matter_id=request.matter.matter_id,
        answer=answer,
        citations=[Citation(document_id=item.document_id, title=item.title) for item in passages],
        follow_up=decide_follow_up(request.matter, request.as_of),
    )
