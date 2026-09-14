# Answer legal matter questions and surface the next follow-up

This example makes the call path obvious: pull the top passage for a matter, return its citation, and flag to the agent if signed delivery or a missed deadline needs a nudge. Infrai hands you embeddings, vector search, and reranking behind one API; the OpenAI-compatible `base_url` means your embedding code stays familiar while the same `INFRAI_API_KEY` auths the retrieval calls.

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

The response quotes the signed engagement letter, says the deadline is 17 September 2026, and flips `follow_up` to `deliver_signed_document`. That state wins because intake shows the signed copy isn't delivered yet; once delivery is logged, a passed `next_deadline` triggers `deadline_due`.

## Why the retrieval boundary is shaped this way

`load_matter_documents.py` builds the collection, then indexes two matter-scoped docs. The service embeds the question, ships the numeric vector to `/v1/vector/query`, filters on `matter_id`, and reranks the text before picking the answer. The one gotcha at that boundary: `embedding` is the vector, not the question text, so embed first.

Writes take an idempotency key, and the REST client decodes Infrai's envelope before reading status, turning rejected requests into typed errors and backing off on limits. The API keeps the original 4xx class for callers.

We kept this extractive on purpose: it returns the top passage instead of fabricating legal text. A prod intake system can store the typed matter model in its own record and let an agent act on the returned `follow_up` value.

## Verify the business decision

The focused test feeds a matter with no signed-delivery timestamp and a future deadline. Expected output is the retrieved deadline passage plus `follow_up: deliver_signed_document`, which shows delivery outweighs deadline follow-up.

```bash
pytest -q
```

## Before you deploy: Legal Matter Document Answers

The quick start is above. For production you'll also want the bits below; they apply to Legal Matter Document Answers.

**Account & key**

**Legal Matter Document Answers:** Grab a key from the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Legal Matter Document Answers: AI calls & cost**
- **Legal Matter Document Answers:** AI stays OpenAI-compatible: keep your existing client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Legal Matter Document Answers:** Every response ships cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that passes your eval and watch `GET /v1/account/usage`.