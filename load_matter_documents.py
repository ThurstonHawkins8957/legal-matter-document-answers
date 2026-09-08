from legal_retrieval import LegalDocument, LegalDocumentIndex


def main() -> None:
    index = LegalDocumentIndex(collection="legal-matter-documents")
    index.prepare()
    index.index(
        [
            LegalDocument(
                document_id="engagement-letter-2026",
                matter_id="MAT-1042",
                title="Signed engagement letter",
                text="The signed engagement letter sets the response deadline at 17 September 2026.",
            ),
            LegalDocument(
                document_id="delivery-receipt-2026",
                matter_id="MAT-1042",
                title="Client delivery receipt",
                text="The client received the countersigned agreement on 28 August 2026.",
            ),
        ]
    )
    print("Indexed 2 documents for matter MAT-1042.")


if __name__ == "__main__":
    main()
