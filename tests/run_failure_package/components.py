from persica.factory.component import AsyncInitializingComponent
from tests.run_failure_package import events


class RunFailureComponent(AsyncInitializingComponent):
    async def initialize(self):
        events.append("initialize")
        raise RuntimeError("run initialize failed")

    async def shutdown(self):
        events.append("shutdown")
