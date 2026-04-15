from persica.factory.component import BaseComponent
from persica.factory.interface import InterfaceFactory
from tests.outside_components import ExternalBaseComponent


class DirectModuleBase:
    pass


class DirectModuleChild(DirectModuleBase):
    pass


class ScannedModuleComponent(BaseComponent):
    pass


class ScannedModuleProduct:
    pass


class ScannedModuleFactory(InterfaceFactory[ScannedModuleProduct]):
    def get_object(self, obj: ScannedModuleProduct | None) -> ScannedModuleProduct:
        return obj if obj is not None else ScannedModuleProduct()


class LocalInheritedComponent(ExternalBaseComponent):
    pass
