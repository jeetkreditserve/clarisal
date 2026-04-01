from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator


_current_actor = ContextVar('clarisal_current_actor', default=None)


def get_current_actor():
    return _current_actor.get()


def set_current_actor(actor):
    return _current_actor.set(actor)


def reset_current_actor(token):
    _current_actor.reset(token)


@contextmanager
def actor_context(actor) -> Iterator[None]:
    token = set_current_actor(actor)
    try:
        yield
    finally:
        reset_current_actor(token)
