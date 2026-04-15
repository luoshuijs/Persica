import asyncio

from persica.application import Application
from persica.factory.component import AsyncInitializingComponent
from tests.run_lifecycle_package import events


class RunLifecycleComponent(AsyncInitializingComponent):
    def __init__(self, application: Application):
        self.application = application

    async def initialize(self):
        events.append("initialize")
        self.application.loop.create_task(self._stop_application())

    async def shutdown(self):
        events.append("shutdown")

    async def _stop_application(self):
        await asyncio.sleep(0)
        self.application.loop.stop()
