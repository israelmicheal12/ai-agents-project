
"""The index and the two retrievers. TODO 3.

Chroma is a black box here, exactly as the syllabus asks. You put vectors in
with metadata and you get ranked ids out. What is worth your attention is
what you put in and how you score what comes back.

Two retrievers, because block 2 compares them:

  dense     embeddings, cosine similarity. Good at meaning, indifferent to
            exact strings.
  keyword   term overlap. The reverse. Deliberately crude, so it is obvious
            what it is doing.
"""

from __future__ import annotations

import json
import re
import urllib.request

from chunking import Chunk

from project.models import EMBED, OLLAMA_URL

EMBED_MODEL = EMBED.name


def embed(texts: list[str], batch: int = 32) -> list[list[float]]:
    """TODO 3a. Embed a list of texts, in batches.

    One call per chunk is the obvious version and it is roughly thirty times
    slower on this corpus. The endpoint takes a list, so give it one.

    POST to f"{OLLAMA_URL}/api/embed" with a JSON body of
    {"model": EMBED_MODEL, "input": [...]} and read the "embeddings" key.
    """

    # Store all the embeddings we receive.
    all_embeddings = []

    # Make sure the batch size is valid.
    if batch <= 0:
        raise ValueError("Batch size must be positive")

    # Process the texts in groups of at most 'batch' items.
    for start in range(0, len(texts), batch):

        # Select the current group of texts.
        group = texts[start:start + batch]

        # Prepare the JSON data expected by Ollama.
        payload = {
            "model": EMBED_MODEL,
            "input": group
        }

        # Convert the dictionary into JSON bytes.
        data = json.dumps(payload).encode("utf-8")

        # Create a request to Ollama's embedding endpoint.
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # Send the request and read the response.
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)

        # Add the returned embeddings to our list.
        all_embeddings.extend(result["embeddings"])

    # Return all the embedding vectors.
    return all_embeddings


class DenseIndex:
    """TODO 3b. Build once per configuration, then query it."""

    def __init__(self, chunks: list[Chunk], name: str = "run_a"):
        """Build the index.

        chromadb.EphemeralClient(), then get_or_create_collection(name),
        then add() with ids, embeddings, and metadatas carrying doc_id and
        section.

        Give the collection a NAME that encodes the configuration. Two
        chunkings have to be able to coexist during the block 3 sweep, and
        rebuilding without deleting is the classic way to end up with two
        chunkings in one index and numbers nobody can explain.

        Keep a dict from chunk_id to Chunk, because search has to map the
        ids Chroma returns back to objects. Set self.dim so the brief's
        conditions line has something to record.
        """

        # Import ChromaDB for storing and searching embeddings.
        import chromadb

        # Keep the original chunks so we can retrieve them by ID.
        self.chunks_by_id = {
            chunk.chunk_id: chunk for chunk in chunks
        }

        # Create an in-memory ChromaDB client.
        self.client = chromadb.EphemeralClient()

        # Create a collection for this experiment.
        # Cosine distance compares the direction of vectors.
        self.collection = self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

        # Start with zero dimensions if the index is empty.
        self.dim = 0

        # Stop if there are no chunks to store.
        if not chunks:
            return

        # Generate embeddings for all the chunk texts.
        vectors = embed([chunk.text for chunk in chunks])

        # Record the number of values in each embedding.
        self.dim = len(vectors[0])

        # Store the chunk IDs, embeddings and source information.
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=vectors,
            metadatas=[
                {
                    "doc_id": chunk.doc_id,
                    "section": chunk.section
                }
                for chunk in chunks
            ]
        )

    def search(self, query: str, k: int = 20) -> list[Chunk]:
        """Embed the query, ask the collection, map ids back to Chunks."""

        # Return no results if the index is empty.
        if not self.chunks_by_id or k <= 0:
            return []

        # Generate an embedding for the user's question.
        query_vector = embed([query])[0]

        # Search ChromaDB for the closest vectors.
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(k, len(self.chunks_by_id))
        )

        # Get the matching chunk IDs in ranked order.
        ranked_ids = results["ids"][0]

        # Find the original Chunk object for each ID.
        ranked_chunks = [
            self.chunks_by_id[chunk_id]
            for chunk_id in ranked_ids
        ]

        # Return the most relevant chunks first.
        return ranked_chunks


def keyword_search(chunks: list[Chunk], query: str,
                   k: int = 20) -> list[Chunk]:
    """TODO 3c. Term overlap. No model, no cost.

    Score each chunk by how many query terms appear in it, return the top k.
    Crude on purpose: in block 2 you will see a document that repeats a term
    in the wrong section outrank the section that answers the question.

    Break ties deterministically, by chunk_id, or two runs of your own code
    will disagree and you will spend ten minutes blaming the embedder.
    """

    # Return no results if k is zero or negative.
    if k <= 0:
        return []

    # Convert the question into lowercase words.
    # A set prevents repeated query words from counting twice.
    query_terms = set(re.findall(r"\w+", query.lower()))

    # Create a list to store each chunk and its score.
    scored_chunks = []

    # Go through all the chunks.
    for chunk in chunks:

        # Convert the chunk text into lowercase words.
        chunk_terms = set(re.findall(r"\w+", chunk.text.lower()))

        # Count how many query words appear in this chunk.
        score = len(query_terms.intersection(chunk_terms))

        # Keep both the score and the original chunk.
        scored_chunks.append((score, chunk))

    # Sort by highest score first.
    # If scores are equal, sort by chunk_id for consistent results.
    scored_chunks.sort(
        key=lambda item: (-item[0], item[1].chunk_id)
    )

    # Take only the first k ranked chunks.
    top_chunks = scored_chunks[:k]

    # Return the original chunks without their scores.
    return [chunk for score, chunk in top_chunks]
