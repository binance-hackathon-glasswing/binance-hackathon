"""Shared, additive development ports. Implementations receive immutable values.

No port alone grants signing authority. See docs/build/PARALLEL_BUILD.md.
"""

from typing import Protocol

from larp.contracts import DecisionSnapshot, Document, PolicyState, Proposal


class Assessor(Protocol):
    def assess(self, request: Document) -> Document: ...


class Market(Protocol):
    def observe(self, request: Document) -> Document: ...


class Policy(Protocol):
    def decide(self, snapshot: DecisionSnapshot, state: PolicyState) -> Proposal: ...


class Planner(Protocol):
    def plan(self, snapshot: DecisionSnapshot, proposal_or_none: Proposal | None) -> Document: ...


class Execution(Protocol):
    def advance(self, state: Document, observation: Document) -> Document: ...


class Store(Protocol):
    def commit(self, batch: Document) -> Document: ...


class Receiver(Protocol):
    def deliver(self, event: Document) -> Document: ...
