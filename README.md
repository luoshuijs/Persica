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

## Future
- [ ] Support full path scanning
- [ ] Support custom factory assembly
