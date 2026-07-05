from __future__ import annotations

from typing import TYPE_CHECKING, overload

from .typing import TrajectoryData, TrajectoryNode

if TYPE_CHECKING:
    from pathlib import Path

    from .typing import TrajectoryStep


class Trajectory:
    def __init__(self):
        self._nodes: dict[int, TrajectoryNode] = {}
        self._path: list[int] = []

    def __len__(self) -> int:
        return len(self._path)

    @overload
    def __getitem__(self, idx: int) -> TrajectoryStep: ...

    @overload
    def __getitem__(self, idx: slice) -> list[TrajectoryStep]: ...

    def __getitem__(self, idx: slice | int) -> list[TrajectoryStep] | TrajectoryStep:
        if isinstance(idx, int):
            return self._nodes[self._path[idx]].step
        return [self._nodes[i].step for i in self._path[idx]]

    def __iter__(self):
        return (self._nodes[i].step for i in self._path)

    def add(self, step: TrajectoryStep):
        node_idx = step.idx
        parent_idx = self._path[-1] if self._path else None

        node = TrajectoryNode(node_idx=node_idx, parent_idx=parent_idx, step=step)

        self._nodes[node_idx] = node
        self._path.append(node_idx)

    def go_back_to(self, step: TrajectoryStep):
        node_idx = step.idx
        if node_idx not in self._nodes:
            raise ValueError(f"Node '{node_idx}' does not exist.")
        if node_idx not in self._path:
            raise ValueError(f"Node '{node_idx}' is not in the trajectory path.")

        self._path = self._path[: self._path.index(node_idx) + 1]

    def save(self, output_path: Path):
        data = TrajectoryData(nodes=self._nodes, path=self._path)
        with output_path.open("w") as f:
            f.write(data.model_dump_json(indent=2))
