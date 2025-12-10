from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

from core.graph_engine.state import NeuralState
from core.graph_engine.node import BaseNode
from core.utils.logger import get_logger
from core.config import settings

logger = get_logger("NeuralGraphEngine")

Condition = Callable[[NeuralState], bool]


@dataclass
class Edge:
    source: str
    target: str
    condition: Optional[Condition] = None


class NeuralGraphEngine:
    """Enterprise-friendly graph engine.

    Özellikler:
    - Node register
    - Koşullu geçişler
    - Cycle / max step koruması
    - Basit retry mekanizması (global)
    """

    def __init__(self, max_retries: int | None = None) -> None:
        self._nodes: Dict[str, BaseNode] = {}
        self._edges: List[Edge] = []
        self._start: Optional[str] = None
        self._max_retries = max_retries or settings.MAX_RETRIES

    def add_node(self, node: BaseNode) -> "NeuralGraphEngine":
        if node.name in self._nodes:
            raise ValueError(f"Node already exists: {node.name}")
        self._nodes[node.name] = node
        if self._start is None:
            self._start = node.name
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[Condition] = None,
    ) -> "NeuralGraphEngine":
        if source not in self._nodes or target not in self._nodes:
            raise KeyError("Both source and target must be registered before adding an edge.")
        self._edges.append(Edge(source=source, target=target, condition=condition))
        return self

    def set_start(self, name: str) -> "NeuralGraphEngine":
        if name not in self._nodes:
            raise KeyError(f"Unknown node: {name}")
        self._start = name
        return self

    async def execute(self, state: NeuralState) -> NeuralState:
        if self._start is None:
            raise RuntimeError("No start node configured.")

        current: Optional[str] = self._start
        visited: Set[str] = set()
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        while current is not None:
            if current in visited:
                logger.error("Cycle detected", extra={"run_id": state.run_id, "node": current})
                state.add_error(
                    error_type="graph_cycle",
                    message=f"Cycle detected at node {current}",
                )
                break
            visited.add(current)

            node = self._nodes[current]
            logger.info(
                "Executing node",
                extra={"run_id": state.run_id, "node": current, "step": state.step},
            )

            retries = 0
            while retries <= self._max_retries:
                try:
                    state.next_step()
                    state = await node.execute(state)
                    break
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error(
                        "Node execution failed",
                        extra={
                            "run_id": state.run_id,
                            "node": current,
                            "error": str(exc),
                            "retries": retries,
                        },
                        exc_info=True,
                    )
                    state.add_error(
                        error_type="node_execution",
                        message=str(exc),
                        details={"node": current, "retries": retries},
                    )
                    retries += 1
                    if retries > self._max_retries:
                        raise

            # süre kontrolü
            if loop.time() - start_time > settings.MAX_EXECUTION_TIME:
                logger.error(
                    "Graph execution timeout",
                    extra={"run_id": state.run_id, "max_execution_time": settings.MAX_EXECUTION_TIME},
                )
                state.add_error(
                    error_type="graph_timeout",
                    message="Max execution time exceeded.",
                )
                break

            # sonraki node
            next_node: Optional[str] = None
            for edge in self._edges:
                if edge.source == current and (edge.condition is None or edge.condition(state)):
                    next_node = edge.target
                    break

            current = next_node

        return state
