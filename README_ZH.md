<h1 style="text-align: center;">Persica</h1>

<div style="text-align: center;">
<img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="">
<img src="https://img.shields.io/badge/works%20on-my%20machine-brightgreen" alt="">
<img src="https://img.shields.io/badge/status-%E5%92%95%E5%92%95%E5%92%95-blue" alt="">
<a href="https://black.readthedocs.io/en/stable/index.html"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code_style" /></a>
</div>

# 介绍
> Persica 这个名字来源于作者最喜欢的角色的拉丁文名，该角色具有鲜明的外貌特点。
>
> *雪霁梅花开，春来蝴蝶飞*。

## 设计灵感

本框架的设计灵感来源于 [spring-framework](https://github.com/spring-projects/)
特别是对于其强大的自动装配功能受到震撼。

## 快速开始

`build()` 是同步的，只负责构造应用对象。`run()` 会使用已配置的事件循环；如果没有提供，就在运行时自行创建，并在应用停止前持续运行。如果你传入了自己的事件循环，它不能已经处于运行状态。

```python
from persica.applicationbuilder import ApplicationBuilder

app = ApplicationBuilder().set_scanner_package("example_app").build()

# 会一直阻塞到应用停止，例如按下 Ctrl+C。
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

## 应用级资源发布

应用对象可以通过 `Application.provide_objects()` 发布运行时资源，这些资源会和组件发布的资源一样参与注入。它们在 `build()` 完成后就已经可用，不需要等到 `run()` 开始。

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

from example_app.application import GreetingService


class GreetingPrinter(AsyncInitializingComponent):
    greeting_service: GreetingService = inject()

    async def initialize(self):
        print(self.greeting_service.greet())
```

```python
# example_app/main.py
from example_app.application import ExampleApplicationBuilder


app = ExampleApplicationBuilder().set_scanner_package("example_app").build()

# build() 仍然是同步的；run() 负责启动初始化并阻塞运行。
app.run()
```

## Future
- [ ] 支持完整路径扫描
- [ ] 支持自定义工厂装配
