from __future__ import annotations

from .current_actor import actor_context


class CurrentActorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actor = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        with actor_context(actor):
            return self.get_response(request)
