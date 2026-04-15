from persica.factory.component import AsyncInitializingComponent
from tests.lifecycle_failure_package import events


class SuccessfulComponent(AsyncInitializingComponent, order=10):
    async def initialize(self):
        events.append("initialize:success")


class FailingComponent(AsyncInitializingComponent, order=20):
    async def initialize(self):
        events.append("initialize:failure")
        raise RuntimeError("initialize failed")
