<h1 style="text-align: center;">Persica</h1>

<div style="text-align: center;">
<img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="">
<img src="https://img.shields.io/badge/works%20on-my%20machine-brightgreen" alt="">
<img src="https://img.shields.io/badge/status-%E5%92%95%E5%92%95%E5%92%95-blue" alt="">
<a href="https://black.readthedocs.io/en/stable/index.html"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code_style" /></a>
</div>

# Introduction
> The name "Persica" is derived from the Latin name of the author's favorite character, known for her distinctive appearance.
>
> "Plum blossoms bloom after the snow, butterflies fly with the spring breeze."

## Design Inspiration
The design inspiration for this framework comes from the [Spring Framework](https://github.com/spring-projects/). 
I am especially impressed by its powerful automatic assembly feature.

## Quick Start
`build()` is synchronous and only constructs the application object. `run()` uses the configured event loop, creating one only when needed, and keeps the application alive until it is stopped. If you pass your own loop, it must not already be running.

```python
from persica.applicationbuilder import ApplicationBuilder

app = ApplicationBuilder().set_scanner_package("example_app").build()

# Blocks until the application is stopped, for example with Ctrl+C.
app.run()
```

```python
# example_app/components.py
from persica.factory.component import AsyncInitializingComponent


class HelloComponent(AsyncInitializingComponent):
    async def initialize(self):
        print("Persica is running")

    async def shutdown(self):
        print("Persica stopped")
```

App-level resources can be published through `Application.provide_objects()` and injected the same way as component-published resources. They are available as soon as the app is built, before `run()` starts creating components.

```python
# example_app/application.py
from persica import inject
from persica.application import Application
from persica.applicationbuilder import ApplicationBuilder


class GreetingService:
    def greet(self) -> str:
        return "hello from the application"


class ExampleApplication(Application):
    def __init__(self, *args, **kwargs):
        self.greeting_service = GreetingService()
        super().__init__(*args, **kwargs)

    def provide_objects(self) -> list[GreetingService]:
        return [self.greeting_service]


class ExampleApplicationBuilder(ApplicationBuilder):
    _application_class = ExampleApplication
```

```python
# example_app/components.py
from persica import inject
from persica.factory.component import AsyncInitializingComponent

from example_app.application import ExampleApplicationBuilder, GreetingService


class GreetingPrinter(AsyncInitializingComponent):
    greeting_service: GreetingService = inject()

    async def initialize(self):
        print(self.greeting_service.greet())
```

```python
# example_app/main.py
from example_app.application import ExampleApplicationBuilder


app = ExampleApplicationBuilder().set_scanner_package("example_app").build()

# build() is still synchronous; run() starts initialization and blocks.
app.run()
```

## Future
- [ ] Support full path scanning
- [ ] Support custom factory assembly
