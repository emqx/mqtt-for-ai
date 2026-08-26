import asyncio
from typing import Protocol

from a2a_over_mqtt import A2ARequest, Responder


class _StreamCallback(Protocol):
    async def __call__(self, message: str, *, type: str = "text") -> None: ...


class ResponderRunner:
    """Fixture-owned lifecycle for Responder background tasks."""

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[None]] = []

    def start(self, responder: Responder) -> asyncio.Task[None]:
        task = asyncio.create_task(responder.run())
        self._tasks.append(task)
        return task

    async def close(self) -> None:
        for task in self._tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)


class EchoResponder(Responder):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.requests: list[A2ARequest] = []

    async def on_request(
        self,
        request: A2ARequest,
        stream: _StreamCallback,
    ) -> str:
        self.requests.append(request)
        await stream("working on it")
        return f"echo: {request.text}"


class ControlledResponder(Responder):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.requests: list[A2ARequest] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def on_request(
        self,
        request: A2ARequest,
        stream: _StreamCallback,
    ) -> str:
        self.requests.append(request)
        self.started.set()
        await stream("waiting for release")
        await self.release.wait()
        return f"echo: {request.text}"
