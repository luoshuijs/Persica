from persica.factory.component import AsyncInitializingComponent
from tests.lifecycle_rescan_package import events


class RescanLifecycleComponent(AsyncInitializingComponent):
    async def initialize(self):
        events.append("initialize:rescan")

    async def shutdown(self):
        events.append("shutdown:rescan")
