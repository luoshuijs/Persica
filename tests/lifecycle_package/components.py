from persica.factory.component import AsyncInitializingComponent
from tests.lifecycle_package import events


class LateComponent(AsyncInitializingComponent, order=20):
    async def initialize(self):
        events.append("initialize:late")

    async def shutdown(self):
        events.append("shutdown:late")


class EarlyComponent(AsyncInitializingComponent, order=10):
    async def initialize(self):
        events.append("initialize:early")

    async def shutdown(self):
        events.append("shutdown:early")


class DefaultOrderComponent(AsyncInitializingComponent):
    async def initialize(self):
        events.append("initialize:default")

    async def shutdown(self):
        events.append("shutdown:default")
