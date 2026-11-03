"""Explicitly build or rebuild the local E5/Chroma policy index."""

import argparse
import sys
from pathlib import Path

from emporio_music.domain.errors import PolicyRetrievalError
from emporio_music.infrastructure.policy_embeddings import E5_CONFIG, E5Embedder
from emporio_music.infrastructure.policy_index import PolicyIndex
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.index_setup import (
    POLICY_COLLECTION,
    load_verified_policy_corpus,
    policy_document_text,
    policy_index_configuration,
)


def prepare_policy_index(
    *,
    data_directory: Path = DATA_DIRECTORY,
    allow_download: bool = False,
    rebuild: bool = False,
) -> int:
    """Build the runtime collection from verified source records."""
    corpus, _, chunks_sha256 = load_verified_policy_corpus(data_directory)
    chunks = [chunk for chunk in corpus.chunks if chunk.indexable]
    configuration = policy_index_configuration(corpus, chunks_sha256, E5_CONFIG)
    index = PolicyIndex(
        data_directory / "policies" / "policy-indexes",
        POLICY_COLLECTION,
        configuration,
    )
    if index.exists() and not rebuild:
        raise ValueError("Policy index already exists; pass --rebuild to replace it")

    embedder = E5Embedder(allow_download=allow_download)
    vectors = embedder.embed(
        [policy_document_text(chunk) for chunk in chunks],
        query=False,
    )
    index.build(chunks, vectors, rebuild=rebuild)
    return len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="allow downloading the pinned E5 model when it is not cached",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="replace the existing policy-e5 collection",
    )
    args = parser.parse_args()
    try:
        count = prepare_policy_index(
            allow_download=args.allow_download,
            rebuild=args.rebuild,
        )
    except (ImportError, OSError, PolicyRetrievalError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        "Prepared "
        f"{count} policy records in "
        f"{DATA_DIRECTORY / 'policies' / 'policy-indexes'}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
