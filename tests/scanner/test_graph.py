import pytest

from persica.scanner.graph import ClassGraph


@pytest.fixture
def graph():
    return ClassGraph()


class TestGraph:
    def test_add_class(self, graph: "ClassGraph"):
        graph.add_class("Child", {"Parent"}, "module.path")
        assert "Child" in graph.class_to_module
        assert graph.class_to_module["Child"] == "module.path"
        assert "Parent" in graph.graph
        assert graph.graph.has_edge("Parent", "Child")

    def test_find_all_ancestors(self, graph: "ClassGraph"):
        graph.add_class("Child", {"Parent"}, "module.path")
        graph.add_class("Parent", {"Grandparent"}, "module.path")
        ancestors = graph.find_all_ancestors("Child")
        assert ancestors == {"Parent", "Grandparent"}

    def test_find_all_descendants(self, graph: "ClassGraph"):
        graph.add_class("Parent", {"Grandparent"}, "module.path")
        graph.add_class("Child", {"Parent"}, "module.path")
        descendants = graph.find_all_descendants("Parent")
        assert descendants == {"Child"}

    def test_get_class_info(self, graph: "ClassGraph"):
        graph.add_class("Child", {"Parent"}, "module.path")
        class_info = graph.get_class_info("Child")
        assert class_info["ancestors"] == {"Parent"}
        assert class_info["descendants"] == set()
        assert class_info["module_path"] == "module.path"

    def test_get_modules_to_import(self, graph: "ClassGraph"):
        graph.add_class("Parent", set(), "module.path.parent")
        graph.add_class("Child", {"Parent"}, "module.path.child")
        modules = graph.get_modules_to_import("Parent")
        assert modules == {"module.path.parent", "module.path.child"}
