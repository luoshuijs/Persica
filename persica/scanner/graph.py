import networkx as nx


class ConflictInfo:
    def __init__(self, parent: str, child: str, parent_order: int, child_order: int):
        self.parent = parent
        self.child = child
        self.parent_order = parent_order
        self.child_order = child_order

    def __str__(self):
        return f"Conflict: {self.parent} (order {self.parent_order}) should not be before {self.child} (order {self.child_order})"


class LoadOrderConflictError(Exception):
    def __init__(self, conflicts: list[ConflictInfo]):
        self.conflicts = conflicts
        super().__init__()

    def __str__(self):
        return f"Load order conflicts detected: {', '.join(str(conflict) for conflict in self.conflicts)}"


class ClassGraph:
    def __init__(self, default_order: int = 0):
        self.graph = nx.DiGraph()
        self.class_to_module: dict[str, str] = {}  # 存储类名到模块路径的映射
        self.class_to_order: dict[str, int] = {}  # 存储类名到加载顺序的映射
        self.default_order = default_order

    def add_class(self, class_name: str, parent_names: set[str], module_path: str):
        self.class_to_module[class_name] = module_path
        for parent in parent_names:
            self.graph.add_edge(parent, class_name)
        self.class_to_order[class_name] = self.default_order

    def set_order(self, class_name: str, order: int):
        """设置手动加载顺序"""
        self.class_to_order[class_name] = order

    def find_all_ancestors(self, class_name: str) -> set[str]:
        return nx.ancestors(self.graph, class_name)

    def find_all_descendants(self, class_name: str) -> set[str]:
        return nx.descendants(self.graph, class_name)

    def get_class_info(self, class_name: str) -> dict[str, any]:
        return {
            "ancestors": self.find_all_ancestors(class_name),
            "descendants": self.find_all_descendants(class_name),
            "module_path": self.class_to_module.get(class_name),
        }

    def check_conflict(self) -> list[ConflictInfo]:
        """
        检查是否存在加载顺序冲突：
        如果 A 依赖于 B，但 A 的 order 大于 B 的 order，则发生冲突。
        """
        conflicts = []
        for parent, child in self.graph.edges():
            parent_order = self.class_to_order.get(parent, 0)
            child_order = self.class_to_order.get(child, 0)
            if parent_order > child_order:
                conflicts.append(ConflictInfo(parent, child, parent_order, child_order))
        return conflicts

    def topological_sort(self) -> list[str]:
        """
        根据依赖关系和手动设置的顺序执行拓扑排序。
        如果没有冲突，返回拓扑排序后的类名列表。
        """
        conflicts = self.check_conflict()
        if conflicts:
            raise LoadOrderConflictError(conflicts)

        sorted_classes = list(nx.topological_sort(self.graph))
        sorted_classes.sort(key=lambda x: self.class_to_order.get(x, 0))
        return sorted_classes

    def get_modules_to_import(self, class_name: str) -> set[str]:
        """
        获取需要导入的模块集合，以导入指定类及其所有子类。
        """
        descendants = self.find_all_descendants(class_name)
        classes = descendants.union({class_name})
        return {self.class_to_module[cls] for cls in classes if cls in self.class_to_module}
