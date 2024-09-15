from typing import Any, Dict, Set

import networkx as nx


class ClassGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_class(self, class_name: str, parent_names: Set[str]):
        for parent in parent_names:
            self.graph.add_edge(parent, class_name)

    def find_all_ancestors(self, class_name: str) -> Set[str]:
        return nx.ancestors(self.graph, class_name)

    def find_all_descendants(self, class_name: str) -> Set[str]:
        return nx.descendants(self.graph, class_name)

    def get_class_info(self, class_name: str) -> Dict[str, Any]:
        return {"ancestors": self.find_all_ancestors(class_name), "descendants": self.find_all_descendants(class_name)}
