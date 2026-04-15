import asyncio

from persica.factory.component import AsyncInitializingComponent
from tests.shutdown_failure_package import events


class LastShutdownComponent(AsyncInitializingComponent, order=30):
    async def shutdown(self):
        events.append("shutdown:last")
        raise RuntimeError("last shutdown failed")


class MiddleShutdownComponent(AsyncInitializingComponent, order=20):
    async def shutdown(self):
        events.append("shutdown:middle")


class FirstShutdownComponent(AsyncInitializingComponent, order=10):
    async def shutdown(self):
        events.append("shutdown:first")
        raise asyncio.CancelledError("first shutdown cancelled")
