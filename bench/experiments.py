"""Your experiments.  *** YOU EXTEND THIS FILE. ***

Run one experiment, or all of them:

    make experiments MEMBER=alice MACHINE=alice-mbp                 # all
    make experiments MEMBER=alice MACHINE=alice-mbp ONLY=example     # one

``example_point_lookups`` below is the summer 2024 interns' one finished experiment, and it works. Copy its
pattern for each experiment the README asks for (E1-E6), and register each
new function in ``EXPERIMENTS`` at the bottom of this file.

The pattern, for every configuration you measure:
    1. prepare keys and queries OUTSIDE the timed region,
    2. build a fresh index (time it with ``time_build`` if build cost matters),
    3. ``index.reset_stats()``, then time one batch with ``time_batch``,
    4. ``writer.record(index, ...)`` one row,
    5. repeat for ``reps`` replicates.
"""

from __future__ import annotations

import random
import time
from typing import Callable, Optional, Sequence

from bench.cli import parse, parser, writer_from_args
from bench.results import ResultsWriter
from bench.timing import build_memory_bytes, time_batch, time_build
from indexes import ALL_INDEXES, make_index
from loaders.spotify import key_value_pairs, load_tracks
from datagen.synthetic import arrange, point_queries, random_keys, range_queries

SEED = 4300


def example_point_lookups(writer: ResultsWriter, tracks: list[dict], reps: int) -> None:
    """Build cost and point-lookup (hit) cost on track_id as the index grows."""
    pairs = key_value_pairs(tracks, "track_id")  # file order
    rng = random.Random(SEED)

    for n in (1_000, 10_000, len(pairs)):
        subset = pairs[:n]
        queries = [key for key, _ in rng.sample(subset, 500)]  # every query is a hit

        for name in ALL_INDEXES:
            # Memory once per configuration (tracing is slow; never time it).
            memory = build_memory_bytes(lambda: make_index(name), subset)

            for rep in range(reps):
                common = dict(
                    experiment="example", dataset="spotify", key_column="track_id",
                    insert_order="file", n_keys=n, rep=rep,
                )

                index = make_index(name)
                ns = time_build(index, subset)
                writer.record(
                    index, **common, operation="build", operation_param="",
                    n_ops=n, total_ns=ns, memory_bytes=memory,
                )

                index.reset_stats()
                ns = time_batch(index.search, queries)
                writer.record(
                    index, **common, operation="point_hit", operation_param=1.0,
                    n_ops=len(queries), total_ns=ns,
                    height=index.structure_info().get("height", ""),
                )
            print(f"  n={n:>7,}  {name:<14} done", flush=True)


# EXPERIMENT 5
def e5_insert_order(writer: ResultsWriter, tracks: list[dict], reps: int) -> None:
    """Does the order keys arrive in matter? Synthetic keys, four arrival orders."""
    for n in (1_000, 10_000, 100_000):
        keys = random_keys(n, length=8, seed=SEED)
        pairs = [(key, row_id) for row_id, key in enumerate(keys)]
        queries = point_queries(keys, 1_000, hit_rate=1.0, seed=SEED)

        for order in ("random", "sorted", "reversed", "nearly_sorted"):
            ordered = arrange(pairs, order, seed=SEED)

            for name in ALL_INDEXES:
                for rep in range(reps):
                    common = dict(
                        experiment="E5_insert_order", dataset="synthetic",
                        key_column="random_keys_len8", insert_order=order,
                        n_keys=n, rep=rep,
                    )

                    index = make_index(name)
                    ns = time_build(index, ordered)
                    writer.record(
                        index, **common, operation="build", operation_param="",
                        n_ops=n, total_ns=ns,
                        height=index.structure_info().get("height", ""),
                    )

                    index.reset_stats()
                    ns = time_batch(index.search, queries)
                    writer.record(
                        index, **common, operation="point_hit", operation_param=1.0,
                        n_ops=len(queries), total_ns=ns,
                        height=index.structure_info().get("height", ""),
                    )
                print(f"  n={n:>7,}  {order:<14} {name:<14} done", flush=True)

EXPERIMENTS: dict[str, Callable[[ResultsWriter, list[dict], int], None]] = {
    "example": example_point_lookups,
    "E5_insert_order": e5_insert_order,
}

# EXPERIMENT 6
def e6_bplus_order(writer: ResultsWriter, tracks: list[dict], reps: int) -> None:
    """Compare B+ tree performance across different orders."""

    pairs = key_value_pairs(tracks, "track_id")
    tempo_pairs = key_value_pairs(tracks, "tempo")
    tempo_keys = [key for key, _ in tempo_pairs]

    ranges = range_queries(
    tempo_keys,
    n_queries=500,
    selectivity=0.01,
    seed=SEED,
)

    rng = random.Random(SEED)
    queries = [key for key, _ in rng.sample(pairs, 500)]

    miss_queries = [f"missing_track_{i}" for i in range(500)]
    existing_ids = {key for key, _ in pairs}
    assert all(key not in existing_ids for key in miss_queries)

    orders = (3, 4, 8, 16, 32, 64, 128, 256, 512)

    for order in orders:
        for rep in range(reps):
            common = dict(
            experiment="E6_bplus_order",
            dataset="spotify",
            key_column="track_id",
            insert_order="file",
            n_keys=len(pairs),
            rep=rep,
        )
            index = make_index("bplus_tree", order=order)
            ns = time_build(index, pairs)

            writer.record(
            index, **common,
            operation="build",
            operation_param="",
            n_ops=len(pairs),
            total_ns=ns,
        )
            index.reset_stats()
            ns = time_batch(index.search, queries)

            writer.record(
                index, **common,
                operation="point_hit",
                operation_param=1.0,
                n_ops=len(queries),
                total_ns=ns,
                height=index.structure_info().get("height", ""),
            )
            index.reset_stats()
            ns = time_batch(index.search, miss_queries)

            writer.record(
                index, **common,
                operation="point_miss",
                operation_param=0.0,
                n_ops=len(miss_queries),
                total_ns=ns,
                height=index.structure_info().get("height", ""),
        )
            tempo_index = make_index("bplus_tree", order=order)
            tempo_ns = time_build(tempo_index, tempo_pairs)

            tempo_common = dict(
                experiment="E6_bplus_order",
                dataset="spotify",
                key_column="tempo",
                insert_order="file",
                n_keys=len(tempo_pairs),
                rep=rep,
        )

            writer.record(
                tempo_index, **tempo_common,
                operation="build",
                operation_param="",
                n_ops=len(tempo_pairs),
                total_ns=tempo_ns,
            )

            tempo_index.reset_stats()
            ns = time_batch(
                lambda query: tempo_index.range_search(*query),
                ranges,
            )

            writer.record(
                tempo_index, **tempo_common,
                operation="range",
                operation_param=0.01,
                n_ops=len(ranges),
                total_ns=ns,
                height=tempo_index.structure_info().get("height", ""),
        )

EXPERIMENTS: dict[str, Callable[[ResultsWriter, list[dict], int], None]] = {
    "example": example_point_lookups,
    "E5_insert_order": e5_insert_order,
    "E6_bplus_order": e6_bplus_order,
}
    


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = parser("Run your experiments.")
    p.add_argument("--only", choices=sorted(EXPERIMENTS), help="run just this experiment")
    args = parse(p, argv)
    writer = writer_from_args(args)
    tracks = load_tracks()
    names = [args.only] if args.only else list(EXPERIMENTS)
    for name in names:
        print(f"{name}: {args.reps} reps, session {writer.session_id}", flush=True)
        started = time.perf_counter()
        EXPERIMENTS[name](writer, tracks, args.reps)
        print(f"{name}: finished in {time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
