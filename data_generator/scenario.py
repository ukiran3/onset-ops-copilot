"""Synthetic shoot-day state: a small, fixed cast of scenes/equipment whose
values evolve deterministically with elapsed seconds, so backfill (walking
through the past) and live-push (walking through the present) use the exact
same step function.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from loki_client import LogLine, structured_message
from prom_remote_write import Metric

SCENES = ["12A", "12B", "14", "15C"]
# Long enough that scene 12A -- the one the demo/architecture doc's example
# question ("why is scene 12A behind schedule?") is about -- is still active
# through the full backfill window and any reasonable live-demo duration.
# (Was 5h; a single dev/demo session ran the live loop past that without a
# restart, which silently rolled the "current scene" over to 12B and made
# scene_burn_minutes{scene="12A"} stop getting fresh samples. 100h so this
# doesn't recur for the rest of the hackathon.)
SCENE_DURATION_S = 100 * 3600

GENERATORS = ["genny-1", "genny-2"]
MICS = ["wireless-mic-1", "wireless-mic-2", "wireless-mic-3"]
RF_ZONES = ["stage-3", "stage-7", "backlot"]

# The engineered problem: starting at this many seconds into the *live* push
# window, genny-1's load and scene 12A's schedule burn ramp into crisis and
# hold there, with matching incident/schedule log lines fired once.
PROBLEM_START_S = 60
PROBLEM_RAMP_S = 90


def active_scene_index(elapsed_s: float) -> int:
    idx = int(elapsed_s // SCENE_DURATION_S)
    return min(idx, len(SCENES) - 1)


def _rng_for(key: str, bucket: int) -> random.Random:
    return random.Random(f"{key}:{bucket}")


def schedule_burn_minutes(elapsed_s: float, live_elapsed_s: float | None) -> tuple[str, float]:
    scene = SCENES[active_scene_index(elapsed_s)]
    scene_elapsed = elapsed_s % SCENE_DURATION_S
    r = _rng_for("burn", int(elapsed_s // 60))
    baseline = -2.0 + (scene_elapsed / SCENE_DURATION_S) * 6.0 + r.uniform(-0.8, 0.8)

    if live_elapsed_s is not None and live_elapsed_s >= PROBLEM_START_S:
        t = min(1.0, (live_elapsed_s - PROBLEM_START_S) / PROBLEM_RAMP_S)
        crisis_target = 18.0
        baseline = baseline + t * (crisis_target - baseline)

    return scene, round(baseline, 2)


def generator_load_pct(elapsed_s: float, live_elapsed_s: float | None) -> dict[str, float]:
    out = {}
    for i, unit in enumerate(GENERATORS):
        r = _rng_for(f"genload:{unit}", int(elapsed_s // 30))
        baseline = 55 + 10 * math.sin(elapsed_s / 600 + i) + r.uniform(-3, 3)

        if unit == "genny-1" and live_elapsed_s is not None and live_elapsed_s >= PROBLEM_START_S:
            t = min(1.0, (live_elapsed_s - PROBLEM_START_S) / PROBLEM_RAMP_S)
            crisis_target = 97.0
            baseline = baseline + t * (crisis_target - baseline)

        out[unit] = round(max(0.0, min(100.0, baseline)), 1)
    return out


def battery_pct(elapsed_s: float) -> dict[str, float]:
    out = {}
    for device in MICS:
        cycle_s = 3 * 3600  # recharge every ~3h of shoot time
        phase = elapsed_s % cycle_s
        r = _rng_for(f"batt:{device}", int(elapsed_s // 60))
        pct = 100 - (phase / cycle_s) * 90 + r.uniform(-1.5, 1.5)
        out[device] = round(max(0.0, min(100.0, pct)), 1)
    return out


def rf_channel_conflicts(elapsed_s: float) -> dict[str, int]:
    out = {}
    for zone in RF_ZONES:
        r = _rng_for(f"rf:{zone}", int(elapsed_s // 120))
        out[zone] = 1 if r.random() < 0.06 else 0
    return out


def build_metrics(elapsed_s: float, timestamp_ms: int, live_elapsed_s: float | None) -> list[Metric]:
    metrics: list[Metric] = []

    scene, burn = schedule_burn_minutes(elapsed_s, live_elapsed_s)
    metrics.append(Metric("schedule_burn_minutes", burn, {"scene": scene}, timestamp_ms))

    for unit, load in generator_load_pct(elapsed_s, live_elapsed_s).items():
        metrics.append(Metric("generator_load_pct", load, {"unit": unit}, timestamp_ms))

    for device, pct in battery_pct(elapsed_s).items():
        metrics.append(Metric("battery_pct", pct, {"device": device}, timestamp_ms))

    for zone, conflicts in rf_channel_conflicts(elapsed_s).items():
        metrics.append(Metric("rf_channel_conflicts", float(conflicts), {"zone": zone}, timestamp_ms))

    return metrics


# --- Logs -------------------------------------------------------------

CONTINUITY_TAKE_INTERVAL_S = 4 * 60  # a new take logged roughly every 4 min

PROP_SETS = {
    "12A": ["coffee mug", "car keys", "manila folder"],
    "12B": ["coffee mug", "car keys"],
    "14": ["revolver (prop)", "briefcase"],
    "15C": ["briefcase", "umbrella"],
}
WARDROBE = {
    "12A": "grey suit, top button fastened",
    "12B": "grey suit, jacket removed",
    "14": "grey suit, tie loosened",
    "15C": "grey suit, tie removed, sleeves rolled",
}
LIGHTING = {
    "12A": "3-point, key stage-left, 5600K",
    "12B": "3-point, key stage-left, 5600K",
    "14": "low-key, single practical, 3200K",
    "15C": "exterior day, bounce fill",
}


def continuity_note(scene: str, take: int, seeded_mismatch: bool) -> dict:
    props = list(PROP_SETS.get(scene, []))
    wardrobe = WARDROBE.get(scene, "")
    lighting = LIGHTING.get(scene, "")
    comment = "Matches previous take."

    if seeded_mismatch and take == 4:
        # Deliberate continuity break for the demo: coffee mug missing on take 4.
        props = [p for p in props if p != "coffee mug"]
        comment = "NOTE: coffee mug missing from desk this take -- check with props before printing."

    return {
        "scene": scene,
        "take": take,
        "props": props,
        "wardrobe": wardrobe,
        "lighting": lighting,
        "comment": comment,
    }


def build_logs_for_tick(
    elapsed_s: float,
    prev_elapsed_s: float,
    timestamp_ns: int,
    live_elapsed_s: float | None,
) -> list[LogLine]:
    lines: list[LogLine] = []

    prev_scene_idx = active_scene_index(prev_elapsed_s)
    cur_scene_idx = active_scene_index(elapsed_s)
    if cur_scene_idx != prev_scene_idx and prev_elapsed_s > 0:
        new_scene = SCENES[cur_scene_idx]
        lines.append(
            LogLine(
                labels={"job": "schedule"},
                message=structured_message(event="scene_change", scene=new_scene),
                timestamp_ns=timestamp_ns,
            )
        )

    scene = SCENES[cur_scene_idx]
    prev_take_bucket = int(prev_elapsed_s // CONTINUITY_TAKE_INTERVAL_S)
    cur_take_bucket = int(elapsed_s // CONTINUITY_TAKE_INTERVAL_S)
    if cur_take_bucket != prev_take_bucket:
        take_number = (cur_take_bucket % 6) + 1
        note = continuity_note(scene, take_number, seeded_mismatch=(scene == "12A"))
        lines.append(
            LogLine(
                labels={"job": "continuity", "scene": scene, "take": str(take_number)},
                message=structured_message(**note),
                timestamp_ns=timestamp_ns,
            )
        )

    if live_elapsed_s is not None:
        problem_fire_window = (PROBLEM_START_S, PROBLEM_START_S + 10)
        if problem_fire_window[0] <= live_elapsed_s < problem_fire_window[1] and not (
            problem_fire_window[0] <= (live_elapsed_s - 10) < problem_fire_window[1]
        ):
            lines.append(
                LogLine(
                    labels={"job": "incidents"},
                    message=structured_message(
                        severity="critical",
                        unit="genny-1",
                        message="Generator genny-1 load climbing past safe threshold -- possible overheat.",
                    ),
                    timestamp_ns=timestamp_ns,
                )
            )
            lines.append(
                LogLine(
                    labels={"job": "schedule"},
                    message=structured_message(
                        event="schedule_slip",
                        scene=SCENES[active_scene_index(elapsed_s)],
                        reason="generator fault suspected",
                    ),
                    timestamp_ns=timestamp_ns,
                )
            )

    return lines
