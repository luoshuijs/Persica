from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from persica.factory.abstract import AbstractAutowireCapableFactory


class ClassScanner:

    def __init__(self, factory: "AbstractAutowireCapableFactory"):
        self.factory = factory

    def scan(self):
        pass

    def do_scan(self):
        for obj in object.__subclasses__():
            if hasattr(obj, "__is_component__"):
                self.factory.obj_set.add(obj)
