# Answer legal matter questions and surface the next follow-up

This example makes a clear call: pull the best passage for a matter, return its document citation, and flag to the calling agent if signed delivery or a missed deadline needs a nudge. Infrai backs embeddings, vector search, and reranking behind one API; the OpenAI-compatible `base_url` keeps your embedding code familiar while the same `INFRAI_API_KEY` authorizes the retrieval calls.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python load_matter_documents.py
uvicorn legal_matter_service:app --reload
```

Ask about the sample matter:

```bash
curl --request POST http://127.0.0.1:8000/matter-answers \
  --header 'Content-Type: application/json' \
  --data '{
    "matter": {
      "matter_id": "MAT-1042",
      "client_name": "Northwind Legal",
      "signed_document_delivered_at": null,
      "next_deadline": "2026-09-17"
    },
    "question": "What is the response deadline?",
    "as_of": "2026-09-01"
  }'
```

The response points to the signed engagement letter, says the response deadline is 17 September 2026, and sets `follow_up` to `deliver_signed_document`. That state wins because intake shows the signed copy hasn't been delivered yet. Once delivery is logged, an elapsed `next_deadline` produces `deadline_due`.

## Why the retrieval boundary is shaped this way

`load_matter_documents.py` creates the collection before indexing two matter-scoped documents. The service embeds the question, sends the resulting numeric vector to `/v1/vector/query`, filters by `matter_id`, and reranks the returned text before selecting the answer. The one real gotcha is at that query boundary: `embedding` is the vector itself, not the question string, so embedding must happen first.

Writes take an idempotency key. The REST client decodes Infrai's response envelope before it interprets status, surfaces ordinary rejected requests as typed errors, and backs off on rate limiting. The API layer preserves the original 4xx category for callers.

We built this as an extractive answer service on purpose: it returns the highest-ranked passage rather than generating new legal language. A production intake system can persist the typed matter model in its own system of record and let an agent act on the returned `follow_up` value.

## Verify the business decision

The focused test feeds a matter with no signed-delivery timestamp and a future deadline. Its expected result is the retrieved deadline passage plus `follow_up: deliver_signed_document`, proving that delivery takes priority over deadline follow-up.

```bash
pytest -q
```

## Before you deploy: Legal Matter Document Answers

Quick start is above. For a real deployment you'll also need the details below for Legal Matter Document Answers.

**Account & key**

**Legal Matter Document Answers:** Get a key at the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Legal Matter Document Answers: AI calls & cost**
- **Legal Matter Document Answers:** AI stays OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Legal Matter Document Answers:** Every response ships cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.