export interface VectorChunkMetadata {
  readonly ownerUserId: string;
  readonly tenantId: string;
  readonly knowledgeBaseId: string;
  readonly documentId: string;
  readonly chunkId: string;
}

export interface BuildVectorChunkMetadataInput {
  readonly ownerUserId: string;
  readonly tenantId: string;
  readonly knowledgeBaseId: string;
  readonly documentId: string;
  readonly chunkId: string;
}

export function buildVectorChunkMetadata(input: BuildVectorChunkMetadataInput): VectorChunkMetadata {
  return {
    ownerUserId: input.ownerUserId,
    tenantId: input.tenantId,
    knowledgeBaseId: input.knowledgeBaseId,
    documentId: input.documentId,
    chunkId: input.chunkId
  };
}
