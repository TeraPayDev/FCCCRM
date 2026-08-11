#!/usr/bin/env python3
"""Dependency-free concurrent smoke/load probe for CRAM HTTP endpoints."""
from __future__ import annotations

import argparse
import concurrent.futures
import statistics
import time
import urllib.request


def hit(url: str, timeout: float) -> tuple[bool, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read(64)
            return 200 <= response.status < 400, time.perf_counter() - started
    except Exception:
        return False, time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda _: hit(args.url, args.timeout), range(args.requests)))
    durations = [duration * 1000 for _, duration in results]
    successes = sum(ok for ok, _ in results)
    p95 = sorted(durations)[max(0, int(len(durations) * 0.95) - 1)]
    print(f"requests={args.requests} success={successes} failure={args.requests-successes} mean_ms={statistics.fmean(durations):.2f} p95_ms={p95:.2f}")
    return 0 if successes == args.requests else 1


if __name__ == "__main__":
    raise SystemExit(main())
