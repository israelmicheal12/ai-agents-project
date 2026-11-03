"""Chunking. TODO 1.

One decision, two numbers, and they trade against each other. Smaller chunks
raise the chance that a retrieved passage is entirely on topic and lower the
chance that the whole answer is inside one of them. Larger chunks do the
reverse.

The thing that makes the trade measurable is that every chunk keeps its
doc_id and its section. The gold set names sections, the scorer resolves
sections to chunk ids at scoring time, and so the same gold set scores any
size you try. If chunks lost their section, changing the chunker would
invalidate the gold set and the sweep in block 3 would be impossible.
"""

from __future__ import annotations

from dataclasses import dataclass

from .corpus_loader import Section, load_sections


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    section: str
    text: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.doc_id, self.section)


def chunk_sections(sections: list[Section], size: int = 600,
                   overlap: int = 80) -> list[Chunk]:
    """TODO 1. Split each section into chunks, keeping its identity.

    Return a list of Chunk. Every chunk carries the doc_id and the section
    it came from, because the gold set names sections and the scorer
    resolves them at scoring time. Lose that and the chunk sweep in block 3
    becomes impossible.

    Two details that are easy to get wrong and expensive to debug.

    Prepend the section heading to the chunk text. A chunk that reads
    "Fees\nThe annual fee is 60 euros" embeds differently from one that
    reads "The annual fee is 60 euros", and the heading is often the only
    place the topic word appears. It is the cheapest retrieval improvement
    in this lab.

    The stride is `size - overlap`, not `size`. Get it wrong and you either
    drop text between chunks or repeat almost all of it, and both look fine
    until a number goes missing from the middle of a section.
    """
    # Check that the chunk size and overlap are valid.
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Invalid size or overlap")

    # Create an empty list to store all chunks.
    chunks = []

    # Calculate how far to move forward for each chunk.
    stride = size - overlap

    # Go through each section of the documents.
    for section in sections:

        # Get the text of the current section.
        text = section.text

        # Split the section text into overlapping pieces.
        for start in range(0, len(text), stride):

            # Take up to 'size' characters from this position.
            part = text[start:start + size]

            # Create a chunk with its original document information.
            chunk = Chunk(
                chunk_id=f"{section.doc_id}::{section.section}::{start}",
                doc_id=section.doc_id,
                section=section.section,
                text=f"{section.section}\n{part}"
            )

            # Add this chunk to our list.
            chunks.append(chunk)

            # Stop when we have reached the end of the section.
            if start + size >= len(text):
                break

    # Return all the chunks.
    return chunks


def load_chunks(size: int = 600, overlap: int = 80) -> list[Chunk]:
    return chunk_sections(load_sections(), size=size, overlap=overlap)
