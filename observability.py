import logging
import os
import time
from collections import deque
from threading import Lock
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("app")


class Metrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.requests = 0
        self.errors = 0
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.latencies: deque[float] = deque(maxlen=100)
        self.request_log: deque[dict[str, Any]] = deque(maxlen=50)
        self.llm_log: deque[dict[str, Any]] = deque(maxlen=50)
        self.started = time.time()

    def record_request(self, error: bool, **detail: Any) -> None:
        with self._lock:
            self.requests += 1
            self.errors += int(error)
            self.request_log.append({"time": time.strftime("%H:%M:%S"), "error": error, **detail})

    def record_llm(self, seconds: float, in_tok: int, out_tok: int, **detail: Any) -> None:
        with self._lock:
            self.llm_calls += 1
            self.input_tokens += in_tok
            self.output_tokens += out_tok
            self.latencies.append(seconds)
            self.llm_log.append(
                {"time": time.strftime("%H:%M:%S"), "latency_s": round(seconds, 3),
                 "input_tokens": in_tok, "output_tokens": out_tok, **detail}
            )

    def record_llm_error(self, error: str, **detail: Any) -> None:
        with self._lock:
            self.llm_log.append({"time": time.strftime("%H:%M:%S"), "error": error, **detail})

    def detail(self, name: str) -> list[dict[str, Any]] | None:
        with self._lock:
            if name == "requests":
                return list(self.request_log)
            if name == "errors":
                return [r for r in self.request_log if r["error"]] + [
                    r for r in self.llm_log if "error" in r
                ]
            if name in {"llm_calls", "input_tokens", "output_tokens",
                        "llm_latency_avg_s", "llm_latency_p95_s"}:
                return list(self.llm_log)
            return None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            lat = sorted(self.latencies)
            return {
                "uptime_s": round(time.time() - self.started),
                "requests": self.requests,
                "errors": self.errors,
                "llm_calls": self.llm_calls,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "llm_latency_avg_s": round(sum(lat) / len(lat), 3) if lat else None,
                "llm_latency_p95_s": round(lat[int(len(lat) * 0.95)], 3) if lat else None,
            }


metrics = Metrics()


class MonitoringHandler(BaseCallbackHandler):
    """Logs every LLM call and feeds latency/token metrics."""

    def __init__(self) -> None:
        self._starts: dict[UUID, float] = {}

    def on_chat_model_start(
        self, serialized: dict[str, Any], messages: list[list[Any]], *, run_id: UUID, **kwargs: Any
    ) -> None:
        self._starts[run_id] = time.perf_counter()
        log.debug("llm start run_id=%s messages=%s", run_id, messages)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        elapsed = time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        usage = getattr(response.generations[0][0], "message", None)
        usage = getattr(usage, "usage_metadata", None) or {}
        in_tok, out_tok = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        metrics.record_llm(elapsed, in_tok, out_tok, run_id=str(run_id)[:8])
        log.info("llm end run_id=%s %.2fs tokens in=%s out=%s", run_id, elapsed, in_tok, out_tok)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        self._starts.pop(run_id, None)
        metrics.record_llm_error(repr(error), run_id=str(run_id)[:8])
        log.error("llm error run_id=%s %r", run_id, error)
