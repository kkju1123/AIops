"""Tenant ownership helpers for vector chunk metadata."""

from __future__ import annotations


def build_vector_chunk_metadata(
    *,
    owner_user_id: str,
    tenant_id: str,
    knowledge_base_id: str,
    document_id: str,
    chunk_id: str,
) -> dict[str, str]:
    """Build metadata every vector chunk must carry before indexing."""
    return {
        "ownerUserId": owner_user_id,
        "tenantId": tenant_id,
        "knowledgeBaseId": knowledge_base_id,
        "documentId": document_id,
        "chunkId": chunk_id,
    }
