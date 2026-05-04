from persica import inject
from persica.factory.component import BaseComponent
from tests.repeated_run_publish_package.shared import RepeatedRunPublishedResource


class RepeatedRunPublishedResourceConsumer(BaseComponent):
    resource: RepeatedRunPublishedResource = inject()
