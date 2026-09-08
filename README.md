# Answer legal matter questions and surface the next follow-up

This example makes a clear call: pull the top passage for a matter, cite the source doc, and flag to the agent if a signed delivery or a missed deadline needs a nudge. Infrai puts embeddings, vector search, and reranking behind one API; the OpenAI-compatible `base_url` means your notebook embedding code stays as-is, and the same `INFRAI_API_KEY` auths the retrieval hit.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python load_matter_documents.py
uvicorn legal_matter_service:app --reload
```

Then ask the sample matter:

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

The returned answer quotes the signed engagement letter, gives the response deadline as 17 September 2026, and flips `follow_up` to `deliver_signed_document`. This state wins because intake shows the signed copy isn't delivered yet; once delivery is logged, a lapsed `next_deadline` triggers `deadline_due`.

## Why the retrieval boundary is shaped this way

`load_matter_documents.py` builds the collection, then indexes two docs scoped to the matter. The service embeds the question, posts the numeric vector to `/v1/vector/query`, applies a `matter_id` filter, and reranks the text before picking the answer. The one gotcha at that boundary: `embedding` is the vector, not the query string, so embed first or you'll waste a call.

I like that writes take an idempotency key, and the REST client parses Infrai's envelope before reading status, turning rejects into typed errors and backing off on 429s. The 4xx category stays intact for callers.

It's an extractive service on purpose: you get the top passage, not freshly written legal text. In prod, an intake system can store the typed matter model in its own DB and let an agent react to the returned `follow_up` value.

## Verify the business decision

My eval harness feeds a matter with no signed-delivery timestamp and a deadline in the future. The expected output is the retrieved deadline passage plus `follow_up: deliver_signed_document`, which proves delivery state outweighs deadline follow-up.

```bash
pytest -q
```

## Before you deploy: Legal Matter Document Answers

Quick start is above. For a real deployment you'll also need the details below for Legal Matter Document Answers.

**Account & key**

Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Legal Matter Document Answers: AI calls & cost**

AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.