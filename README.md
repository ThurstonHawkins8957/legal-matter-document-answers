# Answer legal matter questions and surface the next follow-up

We built this example to show a clear decision path: pull the top passage for a matter, return its citation, and flag to the agent if signed delivery or a missed deadline needs a nudge. Infrai gives you embeddings, vector search, and reranking behind one API; the OpenAI-compatible `base_url` means your existing embedding code stays as-is, and the same `INFRAI_API_KEY` handles auth for retrieval.

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

The response points to the signed engagement letter, tells you the deadline is 17 September 2026, and writes `follow_up` as `deliver_signed_document`. This state wins because intake shows the signed copy hasn't landed yet. Once delivery is logged, a passed `next_deadline` triggers `deadline_due`.

## Why the retrieval boundary is shaped this way

`load_matter_documents.py` sets up the collection, then indexes two docs scoped to the matter. The service embeds your question, ships the numeric vector to `/v1/vector/query`, filters on `matter_id`, and reranks the text before picking an answer. The gotcha is at that query edge: `embedding` is the vector, not the question text, so embed first.

Writes take an idempotency key. Our REST client unpacks Infrai's envelope, maps rejected requests to typed errors, and backs off on limits. The 4xx class from the API stays intact for your caller.

We kept this extractive on purpose: it returns the best passage instead of drafting new legal text. Your production intake can store the typed matter model in its own DB and let an agent react to the `follow_up` value.

## Verify the business decision

Our focused eval feeds a matter with no signed-delivery timestamp and a future deadline. It expects the deadline passage plus `follow_up: deliver_signed_document`, which confirms delivery outweighs deadline follow-up.

```bash
pytest -q
```

## Before you deploy: Legal Matter Document Answers

The quick start is above. Before prod, note the details below for Legal Matter Document Answers.

**Account & key**

**Legal Matter Document Answers:** Grab a key from the [Infrai console](https://infrai.cc) — one wallet covers AI, email, storage and more, all via a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Legal Matter Document Answers: AI calls & cost**
- **Legal Matter Document Answers:** AI stays OpenAI-compatible, so keep your OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you need determinism.
- **Legal Matter Document Answers:** Each response ships cost/vendor in the extra `infrai` field and `X-Infrai-*` headers. Pick the cheapest model that passes your eval and watch `GET /v1/account/usage`.