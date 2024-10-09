import asyncio


class TestApplicationContext:
    async def test_initialize_and_shutdown(self, app):
        loop = asyncio.get_event_loop()
        context = app.context
        await loop.run_in_executor(None, context.run)
        await context.initialize()
        await context.shutdown()
