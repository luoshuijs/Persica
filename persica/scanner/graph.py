from typing import Any, Dict, Iterable, List, Set

import networkx as nx


class ClassGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.class_to_module: Dict[str, str] = {}  # 存储类名到模块路径的映射

    def add_class(self, class_name: str, parent_names: Set[str], module_path: str):
        self.class_to_module[class_name] = module_path
        if parent_names:
            for parent in parent_names:
                self.graph.add_edge(parent, class_name)
        else:
            self.graph.add_node(class_name)

    def find_all_ancestors(self, class_name: str) -> Set[str]:
        return nx.ancestors(self.graph, class_name)

    def find_all_descendants(self, class_name: str) -> Set[str]:
        return nx.descendants(self.graph, class_name)
      
    def find_all_sink(self) -> List[str]:
        out_degree = self.graph.out_degree()
        if isinstance(out_degree, Iterable):
            return [node for node, out_degree in out_degree if out_degree == 0]
        else:
            raise TypeError("out_degree is not iterable")

    def get_class_info(self, class_name: str) -> Dict[str, Any]:
        return {
            "ancestors": self.find_all_ancestors(class_name),
            "descendants": self.find_all_descendants(class_name),
            "module_path": self.class_to_module.get(class_name),
        }

    def get_modules_to_import(self, class_name: str) -> Set[str]:
        """
        获取需要导入的模块集合，以导入指定类及其所有子类。
        """
        descendants = self.find_all_descendants(class_name)
        classes = descendants.union({class_name})
        modules = {self.class_to_module[cls] for cls in classes if cls in self.class_to_module}
        return modules
