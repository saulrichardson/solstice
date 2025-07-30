"""Hybrid reading-order detector for 1- and 2-column pages.

The algorithm works in three stages:

1.  Detect 1 vs. 2 columns using 1-D K-means on the horizontal centres
    of all boxes.  A silhouette proxy decides whether the clustering is
    meaningful; otherwise we fall back to a single column.

2.  Identify *spanning* blocks that cover ≥ 60 % of the page width.  Such
    blocks often bridge columns (e.g. full-width figures).

3.  Build a directed acyclic graph that encodes natural reading
    dependencies:

    • vertical: a box that ends above another and horizontally overlaps
      must come first;
    • horizontal: in the same vertical band, left precedes right;
    • spanning blocks respect both rules.

   A topological sort of this DAG yields the final reading order.  If a
   cycle is detected (rare with proper layout detection) the algorithm
   degrades to a simple top-to-bottom sort.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import List

from .box import Box

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kmeans_1d(points: list[float], max_iter: int = 10) -> list[int]:
    """Very small 1-D K-means for k=2 with deterministic seeds."""

    if len(points) < 2:
        return [0] * len(points)

    centroids = [min(points), max(points)]

    for _ in range(max_iter):
        clusters = ([], [])  # type: ignore[var-annotated]
        for idx, p in enumerate(points):
            ci = 0 if abs(p - centroids[0]) < abs(p - centroids[1]) else 1
            clusters[ci].append(idx)

        new_centroids = []
        for ci, members in enumerate(clusters):
            if members:
                new_centroids.append(sum(points[i] for i in members) / len(members))
            else:  # empty cluster – keep previous position
                new_centroids.append(centroids[ci])

        if all(math.isclose(a, b, rel_tol=1e-3) for a, b in zip(centroids, new_centroids)):
            break
        centroids = new_centroids

    # Final assignment with converged centroids
    # Recompute clusters to ensure they match the final centroids
    clusters = ([], [])  # type: ignore[var-annotated]
    for idx, p in enumerate(points):
        ci = 0 if abs(p - centroids[0]) < abs(p - centroids[1]) else 1
        clusters[ci].append(idx)

    labels = [0] * len(points)
    for ci, members in enumerate(clusters):
        for i in members:
            labels[i] = ci
    return labels


def _silhouette_1d(points: list[float], labels: list[int]) -> float:
    """Crudely approximate silhouette for k=2 on 1-D data."""

    if len(set(labels)) < 2:
        return 0.0

    # Mean intra-cluster distance (a) and inter-cluster distance (b)
    cluster0 = [p for p, l in zip(points, labels) if l == 0]
    cluster1 = [p for p, l in zip(points, labels) if l == 1]

    if not cluster0 or not cluster1:
        return 0.0

    # Compute average intra-cluster distances with consistent scaling
    # Use n*(n-1) for intra-cluster to exclude self-distances
    n0, n1 = len(cluster0), len(cluster1)
    a0 = sum(abs(x - y) for x in cluster0 for y in cluster0) / max(1, n0 * (n0 - 1))
    a1 = sum(abs(x - y) for x in cluster1 for y in cluster1) / max(1, n1 * (n1 - 1))
    a = (a0 + a1) / 2
    
    # Inter-cluster distance uses n*m as before
    b = sum(abs(x - y) for x in cluster0 for y in cluster1) / (len(cluster0) * len(cluster1))
    if b == 0:
        return 0.0
    return (b - a) / max(a, b)


def _horizontal_overlap(a: Box, b: Box) -> bool:
    """Check if two boxes overlap in the horizontal dimension (X-axis).
    
    Returns True if the X ranges of the two boxes overlap.
    bbox format: (x1, y1, x2, y2)
    """
    return not (a.bbox[2] <= b.bbox[0] or b.bbox[2] <= a.bbox[0])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def determine_reading_order(boxes: List[Box]) -> List[str]:
    """Return list of box IDs in natural reading order."""

    if not boxes:
        return []

    page_width = max(b.bbox[2] for b in boxes)
    page_height = max(b.bbox[3] for b in boxes)

    centres = [(b.bbox[0] + b.bbox[2]) / 2 for b in boxes]
    labels = _kmeans_1d(centres)

    # Assess clustering quality – if poor switch to single column.
    if _silhouette_1d(centres, labels) < 0.25 or (
        max(centres) - min(centres)
    ) < 0.15 * page_width:
        labels = [0] * len(boxes)

    spanning = [
        (b.bbox[2] - b.bbox[0]) >= 0.60 * page_width for b in boxes
    ]

    # Build dependency graph
    edges: dict[int, set[int]] = defaultdict(set)

    for i, bi in enumerate(boxes):
        for j, bj in enumerate(boxes):
            if i == j:
                continue

            # bi above bj & overlaps horizontally → edge i -> j
            if bi.bbox[3] <= bj.bbox[1] and _horizontal_overlap(bi, bj):
                edges[i].add(j)
                continue

            # Same vertical band, different columns
            if labels[i] < labels[j] and _horizontal_overlap(bi, bj):
                edges[i].add(j)

            # Spanning blocks serve as bridges
            if spanning[i] and not spanning[j] and bi.bbox[1] <= bj.bbox[1]:
                edges[i].add(j)
            if spanning[j] and not spanning[i] and bj.bbox[1] <= bi.bbox[1]:
                edges[j].add(i)

    # Kahn topo sort
    indeg = {i: 0 for i in range(len(boxes))}
    for deps in edges.values():
        for j in deps:
            indeg[j] += 1

    queue = deque([i for i, d in indeg.items() if d == 0])
    order: list[int] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for tgt in edges.get(node, ()):  # type: ignore[arg-type]
            indeg[tgt] -= 1
            if indeg[tgt] == 0:
                queue.append(tgt)

    if len(order) != len(boxes):  # cycle fallback
        order = sorted(range(len(boxes)), key=lambda i: boxes[i].bbox[1])

    return [boxes[i].id for i in order]

