from typing import Any, Dict, Iterable, List, Set

import networkx as nx


class ClassGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_class(self, class_name: str, parent_names: Set[str]):
        if parent_names:
            for parent in parent_names:
                self.graph.add_edge(parent, class_name)
        else:
            self.graph.add_node(class_name)

    def find_all_ancestors(self, class_name: str) -> Set[str]:
        return nx.ancestors(self.graph, class_name)

    def find_all_descendants(self, class_name: str) -> Set[str]:
        return nx.descendants(self.graph, class_name)

    def get_class_info(self, class_name: str) -> Dict[str, Any]:
        return {"ancestors": self.find_all_ancestors(class_name), "descendants": self.find_all_descendants(class_name)}

    def find_all_sink(self) -> List[str]:
        out_degree = self.graph.out_degree()
        if isinstance(out_degree, Iterable):
            return [node for node, out_degree in out_degree if out_degree == 0]
        else:
            raise TypeError("out_degree is not iterable")
