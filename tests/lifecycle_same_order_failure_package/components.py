import asyncio

from persica.factory.component import AsyncInitializingComponent
from tests.lifecycle_same_order_failure_package import events, get_initialize_gate


class BlockingComponent(AsyncInitializingComponent, order=10):
    async def initialize(self):
        events.append("initialize:blocking:start")
        try:
            await get_initialize_gate().wait()
            events.append("initialize:blocking:finished")
        except asyncio.CancelledError:
            events.append("initialize:blocking:cancelled")
            raise

    async def shutdown(self):
        events.append("shutdown:blocking")


class TriggeringFailureComponent(AsyncInitializingComponent, order=10):
    async def initialize(self):
        events.append("initialize:failing")
        raise RuntimeError("same-order initialize failed")

    async def shutdown(self):
        events.append("shutdown:trigger")
