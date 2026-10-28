from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def request_once(url: str, timeout: float) -> tuple[bool, float, int]:
    started = time.perf_counter()
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=False)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return response.is_success, elapsed_ms, response.status_code
    except httpx.HTTPError:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, elapsed_ms, 0


def run(
    *,
    url: str,
    requests: int,
    concurrency: int,
    timeout: float,
    min_availability: float,
    max_p95_ms: float,
) -> dict[str, float | int]:
    results: list[tuple[bool, float, int]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(request_once, url, timeout)
            for _ in range(requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    successes = sum(1 for ok, _, _ in results if ok)
    latencies = [latency for _, latency, _ in results]
    availability = successes / len(results) if results else 0.0
    summary = {
        "requests": len(results),
        "successes": successes,
        "availability": availability,
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
    }
    print(summary)

    if availability < min_availability:
        raise SystemExit("Availability threshold was not met.")
    if float(summary["p95_ms"]) > max_p95_ms:
        raise SystemExit("p95 latency threshold was not met.")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a bounded PRISM Enterprise staging load smoke."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--min-availability", type=float, default=0.999)
    parser.add_argument("--max-p95-ms", type=float, default=750.0)
    args = parser.parse_args()

    if args.requests < 1 or args.requests > 10000:
        raise SystemExit("--requests must be between 1 and 10000.")
    if args.concurrency < 1 or args.concurrency > 200:
        raise SystemExit("--concurrency must be between 1 and 200.")

    run(
        url=args.url,
        requests=args.requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
        min_availability=args.min_availability,
        max_p95_ms=args.max_p95_ms,
    )


if __name__ == "__main__":
    main()
