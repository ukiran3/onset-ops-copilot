"""Minimal Prometheus remote_write client.

Hand-rolled protobuf wire encoding for prometheus.WriteRequest so we don't
need grpcio-tools or prometheus-client's push machinery -- just `requests`
and `python-snappy`, which we already depend on.

Wire format: https://github.com/prometheus/prometheus/blob/main/prompb/remote.proto
  message WriteRequest { repeated TimeSeries timeseries = 1; }
  message TimeSeries   { repeated Label labels = 1; repeated Sample samples = 2; }
  message Label        { string name = 1; string value = 2; }
  message Sample       { double value = 1; int64 timestamp = 2; }
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass

import requests
import snappy


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _tag(field_number: int, wire_type: int) -> bytes:
    return _varint((field_number << 3) | wire_type)


def _string_field(field_number: int, s: str) -> bytes:
    b = s.encode("utf-8")
    return _tag(field_number, 2) + _varint(len(b)) + b


def _double_field(field_number: int, v: float) -> bytes:
    return _tag(field_number, 1) + struct.pack("<d", v)


def _varint_field(field_number: int, n: int) -> bytes:
    return _tag(field_number, 0) + _varint(n)


def _embedded(field_number: int, payload: bytes) -> bytes:
    return _tag(field_number, 2) + _varint(len(payload)) + payload


def _encode_label(name: str, value: str) -> bytes:
    return _string_field(1, name) + _string_field(2, value)


def _encode_sample(value: float, timestamp_ms: int) -> bytes:
    return _double_field(1, value) + _varint_field(2, timestamp_ms)


@dataclass
class Metric:
    name: str
    value: float
    labels: dict[str, str]
    timestamp_ms: int | None = None


def _encode_timeseries(metric: Metric) -> bytes:
    ts_ms = metric.timestamp_ms if metric.timestamp_ms is not None else int(time.time() * 1000)
    data = b""
    data += _embedded(1, _encode_label("__name__", metric.name))
    for k, v in metric.labels.items():
        data += _embedded(1, _encode_label(k, v))
    data += _embedded(2, _encode_sample(metric.value, ts_ms))
    return data


def encode_write_request(metrics: list[Metric]) -> bytes:
    data = b""
    for m in metrics:
        data += _embedded(1, _encode_timeseries(m))
    return data


class PrometheusRemoteWriter:
    def __init__(self, url: str, username: str, api_key: str, timeout: float = 30.0):
        self.url = url
        self.auth = (username, api_key)
        self.timeout = timeout
        # Reused across pushes: establishing a fresh TLS connection per call
        # is the dominant cost on a high-latency network.
        self.session = requests.Session()

    def push(self, metrics: list[Metric]) -> requests.Response:
        body = encode_write_request(metrics)
        compressed = snappy.compress(body)
        resp = self.session.post(
            self.url,
            data=compressed,
            auth=self.auth,
            headers={
                "Content-Encoding": "snappy",
                "Content-Type": "application/x-protobuf",
                "X-Prometheus-Remote-Write-Version": "0.1.0",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp
