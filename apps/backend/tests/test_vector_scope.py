from super_ai.memory.vector_scope import build_vector_chunk_metadata


def test_vector_chunk_metadata_contains_owner_and_tenant_scope() -> None:
    metadata = build_vector_chunk_metadata(
        owner_user_id="user_1",
        tenant_id="user_1",
        knowledge_base_id="kb_1",
        document_id="doc_1",
        chunk_id="chunk_1",
    )

    assert metadata == {
        "ownerUserId": "user_1",
        "tenantId": "user_1",
        "knowledgeBaseId": "kb_1",
        "documentId": "doc_1",
        "chunkId": "chunk_1",
    }
