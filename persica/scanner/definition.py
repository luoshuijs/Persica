from typing import List, Optional, Type


class ObjectDefinition:
    class_object: Type[object]

    depends_on: List[str]

    factory_name: Optional[str] = None
