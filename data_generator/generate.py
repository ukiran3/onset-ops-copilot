"""Synthetic on-set data generator.

Backfills a few hours of "shoot day so far" history into Grafana Cloud, then
live-pushes new points every ~10s, matching the same step function so the
dashboard reads as one continuous timeline.
"""

import argparse
import time

import config
import scenario
from loki_client import LokiClient
from prom_remote_write import PrometheusRemoteWriter

BACKFILL_STEP_S = 30
METRICS_BATCH_SIZE = 500
LOGS_BATCH_SIZE = 200

# Grafana Cloud's free-tier Mimir ingester rejects metric samples older than a
# fixed out-of-order-time-window (measured empirically at ~105min for this
# stack). Loki has no such limit. Clamp so backfill never crashes mid-run.
MAX_METRICS_BACKFILL_MINUTES = 95


def make_clients() -> tuple[PrometheusRemoteWriter, LokiClient]:
    prom = PrometheusRemoteWriter(
        url=config.GRAFANA_PROMETHEUS_URL,
        username=config.GRAFANA_PROMETHEUS_USERNAME,
        api_key=config.GRAFANA_PROMETHEUS_API_KEY,
    )
    loki = LokiClient(
        url=config.GRAFANA_LOKI_URL,
        username=config.GRAFANA_LOKI_USERNAME,
        api_key=config.GRAFANA_LOKI_API_KEY,
    )
    return prom, loki


def push_in_batches(push_fn, items, batch_size, label):
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        try:
            push_fn(batch)
            print(f"  pushed {label} batch {i // batch_size + 1} ({len(batch)} items)")
        except Exception as e:  # noqa: BLE001 -- backfill should degrade, not crash
            print(f"  WARNING: {label} batch {i // batch_size + 1} failed: {e}")


def backfill(prom: PrometheusRemoteWriter, loki: LokiClient, hours: float) -> float:
    """Push historical data from (now - hours) up to now. Returns the
    elapsed-seconds value that 'now' corresponds to, so live mode continues
    the same timeline."""
    total_s = hours * 3600
    now_wall_ms = int(time.time() * 1000)
    metrics_floor_ms = now_wall_ms - MAX_METRICS_BACKFILL_MINUTES * 60 * 1000

    all_metrics = []
    all_logs = []
    prev_elapsed = 0.0
    steps = int(total_s // BACKFILL_STEP_S)
    metrics_skipped = 0

    print(f"Backfilling {hours}h of history ({steps} steps)...")
    print(
        f"  (metrics limited to trailing {MAX_METRICS_BACKFILL_MINUTES}min: "
        f"Grafana Cloud's free-tier ingester rejects older samples; logs have no such limit)"
    )
    for step in range(steps + 1):
        elapsed = step * BACKFILL_STEP_S
        wall_ms = now_wall_ms - int((total_s - elapsed) * 1000)
        wall_ns = wall_ms * 1_000_000

        if wall_ms >= metrics_floor_ms:
            all_metrics.extend(scenario.build_metrics(elapsed, wall_ms, live_elapsed_s=None))
        else:
            metrics_skipped += 1
        all_logs.extend(
            scenario.build_logs_for_tick(elapsed, prev_elapsed, wall_ns, live_elapsed_s=None)
        )
        prev_elapsed = elapsed

    if metrics_skipped:
        print(f"  (skipped metrics for {metrics_skipped} older steps, kept logs for all of them)")

    push_in_batches(prom.push, all_metrics, METRICS_BATCH_SIZE, "metrics")
    if all_logs:
        push_in_batches(loki.push, all_logs, LOGS_BATCH_SIZE, "logs")

    print(f"Backfill complete: {len(all_metrics)} metric samples, {len(all_logs)} log lines.")
    return total_s


def live_loop(prom: PrometheusRemoteWriter, loki: LokiClient, start_elapsed_s: float, interval_s: float):
    print(f"Entering live push loop (every {interval_s}s). Ctrl+C to stop.")
    live_start_wall = time.time()
    prev_elapsed = start_elapsed_s

    while True:
        live_elapsed = time.time() - live_start_wall
        elapsed = start_elapsed_s + live_elapsed
        wall_ms = int(time.time() * 1000)
        wall_ns = wall_ms * 1_000_000

        metrics = scenario.build_metrics(elapsed, wall_ms, live_elapsed_s=live_elapsed)
        logs = scenario.build_logs_for_tick(elapsed, prev_elapsed, wall_ns, live_elapsed_s=live_elapsed)
        prev_elapsed = elapsed

        prom.push(metrics)
        if logs:
            loki.push(logs)
            for line in logs:
                print(f"  [{line.labels}] {line.message}")

        print(f"tick: elapsed={elapsed:.0f}s live={live_elapsed:.0f}s pushed {len(metrics)} metrics")
        time.sleep(interval_s)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill-hours", type=float, default=2.0)
    parser.add_argument("--interval-s", type=float, default=10.0)
    parser.add_argument("--skip-backfill", action="store_true")
    args = parser.parse_args()

    prom, loki = make_clients()

    if args.skip_backfill:
        start_elapsed_s = args.backfill_hours * 3600
    else:
        start_elapsed_s = backfill(prom, loki, args.backfill_hours)

    live_loop(prom, loki, start_elapsed_s, args.interval_s)


if __name__ == "__main__":
    main()
