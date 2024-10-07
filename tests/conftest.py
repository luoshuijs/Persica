import asyncio
import sys

import pytest

from persica.applicationbuilder import ApplicationBuilder


@pytest.fixture(scope="session")
def event_loop(request):
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.get_event_loop_policy().new_event_loop()



@pytest.fixture
async def app():
    application = (
        ApplicationBuilder()
        .set_scanner_package("tests.test_package")
        .build()
    )
    yield application
