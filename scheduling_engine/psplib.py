"""
PSPLIB `.sm` instance parser and adapter (proposal Sections 3.4, 3.6;
Objective 6: "evaluate the component against PSPLIB benchmark instances
for scheduling correctness and solve time").

PSPLIB instances are the standard, literature-wide benchmark for the
Resource-Constrained Project Scheduling Problem the proposal cites
directly (Kolisch & Sprecher). Validating against them answers a
different question than the unit tests in tests/test_solver.py do: the
unit tests prove the solver obeys the rules I wrote down myself; PSPLIB
proves it also behaves correctly on problem instances nobody on this
project constructed, with the structure, scale and tightness the wider
field actually uses to compare methods (see `_module docstring note`
below on the resource model gap this closes).

PSPLIB's resource model vs. this project's resource model
-----------------------------------------------------------
PSPLIB activities draw some *quantity* from an abstract pool of a given
renewable resource type (e.g. "job 2 consumes 4 units of R1 out of 12
available"), with no notion of which specific unit. The event-scheduling
domain model in scheduling_engine.models is different on purpose: every
resource is a nameable, identifiable thing (a specific photographer, a
specific sound crew), because the planner needs to know *who* is
assigned, not just how many generic units are busy.

To reuse the already-tested solver unmodified, a PSPLIB resource type of
capacity C is materialised here as C distinct interchangeable unit
resources (role f"R{k}", capacity=1 each), and a job's request for q
units of that type becomes ResourceRequirement(role=f"R{k}", count=q).
Requiring q of C identical, mutually-exclusive units at once is exactly
the same feasibility question as "at most C units of this type in use at
once" — the decomposition changes how the model is built, not what it
means. This is also a legitimate thing to say in the viva: it shows the
same solver core serves both the generic RCPSP benchmark and the
domain-specific named-resource model, rather than needing two solvers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from scheduling_engine.models import (
    Activity,
    Event,
    Resource,
    ResourceRequirement,
    ResourceType,
)


class PsplibFormatError(ValueError):
    """The .sm file doesn't match the structure this parser understands."""


@dataclass
class PsplibJob:
    id: int
    duration: int
    successors: list[int] = field(default_factory=list)
    resource_requests: list[int] = field(default_factory=list)  # one per renewable resource, in order


@dataclass
class PsplibInstance:
    name: str
    jobs: list[PsplibJob]
    resource_capacities: list[int]  # one per renewable resource, in order
    critical_path_lower_bound: int  # the file's own "MPM-Time": minimum possible makespan ignoring resources


def parse_sm(path: str | Path) -> PsplibInstance:
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()

    num_renewable = _extract_int(lines, r"^\s*-\s*renewable\s*:\s*(\d+)\s*R")
    num_nonrenewable = _extract_int(lines, r"^\s*-\s*nonrenewable\s*:\s*(\d+)\s*N")
    num_doubly_constrained = _extract_int(lines, r"^\s*-\s*doubly constrained\s*:\s*(\d+)\s*D")
    if num_nonrenewable or num_doubly_constrained:
        raise PsplibFormatError(
            f"{path.name}: this parser only supports purely-renewable-resource "
            f"single-mode instances (got {num_nonrenewable} nonrenewable, "
            f"{num_doubly_constrained} doubly constrained)"
        )

    project_header_idx = _find_line(lines, "PROJECT INFORMATION:")
    project_row = lines[project_header_idx + 2].split()
    critical_path_lower_bound = int(project_row[-1])

    precedence_header_idx = _find_line(lines, "PRECEDENCE RELATIONS:")
    jobs_count = _extract_int(lines, r"^\s*jobs \(incl\. supersource/sink\s*\)\s*:\s*(\d+)")
    successors_by_job: dict[int, list[int]] = {}
    for row_text in lines[precedence_header_idx + 2 : precedence_header_idx + 2 + jobs_count]:
        tokens = [int(t) for t in row_text.split()]
        job_id, _num_modes, num_successors = tokens[0], tokens[1], tokens[2]
        successors_by_job[job_id] = tokens[3 : 3 + num_successors]

    requests_header_idx = _find_line(lines, "REQUESTS/DURATIONS:")
    durations_by_job: dict[int, int] = {}
    requests_by_job: dict[int, list[int]] = {}
    # +3 to skip the header line and the "----" separator line beneath it.
    for row_text in lines[requests_header_idx + 3 : requests_header_idx + 3 + jobs_count]:
        tokens = [int(t) for t in row_text.split()]
        job_id, _mode, duration = tokens[0], tokens[1], tokens[2]
        durations_by_job[job_id] = duration
        requests_by_job[job_id] = tokens[3 : 3 + num_renewable]

    availabilities_header_idx = _find_line(lines, "RESOURCEAVAILABILITIES:")
    resource_capacities = [int(t) for t in lines[availabilities_header_idx + 2].split()]

    jobs = [
        PsplibJob(
            id=job_id,
            duration=durations_by_job[job_id],
            successors=successors_by_job[job_id],
            resource_requests=requests_by_job[job_id],
        )
        for job_id in sorted(durations_by_job)
    ]

    return PsplibInstance(
        name=path.stem,
        jobs=jobs,
        resource_capacities=resource_capacities,
        critical_path_lower_bound=critical_path_lower_bound,
    )


def to_scheduling_model(instance: PsplibInstance) -> tuple[Event, list[Resource]]:
    """Convert a parsed instance into this project's own Activity/Resource
    types, using the unit-materialisation decomposition described in the
    module docstring.
    """
    resources: list[Resource] = []
    for resource_index, capacity in enumerate(instance.resource_capacities, start=1):
        role = f"R{resource_index}"
        for unit in range(1, capacity + 1):
            resources.append(
                Resource(
                    id=f"{instance.name}-{role}-unit-{unit}",
                    name=f"{role} unit {unit}",
                    type=ResourceType.EQUIPMENT,
                    role=role,
                    capacity=1,
                )
            )

    predecessors_by_job: dict[int, list[int]] = {job.id: [] for job in instance.jobs}
    for job in instance.jobs:
        for succ_id in job.successors:
            predecessors_by_job[succ_id].append(job.id)

    activities = [
        Activity(
            id=f"{instance.name}-job{job.id}",
            event_id=instance.name,
            name=f"Job {job.id}",
            duration_minutes=job.duration,
            predecessors=[f"{instance.name}-job{p}" for p in predecessors_by_job[job.id]],
            requirements=[
                ResourceRequirement(role=f"R{i + 1}", count=amount)
                for i, amount in enumerate(job.resource_requests)
                if amount > 0
            ],
        )
        for job in instance.jobs
    ]

    event = Event(id=instance.name, name=instance.name, activities=activities)
    return event, resources


def _find_line(lines: list[str], marker: str) -> int:
    for i, line in enumerate(lines):
        if marker in line:
            return i
    raise PsplibFormatError(f"expected to find a line containing {marker!r}")


def _extract_int(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern)
    for line in lines:
        m = regex.match(line)
        if m:
            return int(m.group(1))
    raise PsplibFormatError(f"expected a line matching {pattern!r}")
