import ast

from persica.scanner.graph import ClassGraph
from persica.scanner.visitor import ClassVisitor

test_visit_simple_class_source_code = """
class A:
    pass
"""


test_visit_inherited_class_source_code = """
class A:
    pass

class B(A):
    pass
"""


test_visit_imported_base_class_source_code = """
from other.module import BaseClass

class Derived(BaseClass):
    pass
"""

test_resolve_full_name_source_code = """
import other.module as om

class Derived(om.BaseClass):
    pass
"""


class TestClassVisitor:
    def test_visit_simple_class(self):
        tree = ast.parse(test_visit_simple_class_source_code)
        graph = ClassGraph()
        visitor = ClassVisitor(graph, "module.test")
        visitor.visit(tree)
        assert graph.class_to_module["module.test.A"] == "module.test"

    def test_visit_inherited_class(self):
        tree = ast.parse(test_visit_inherited_class_source_code)
        graph = ClassGraph()
        visitor = ClassVisitor(graph, "module.test")
        visitor.visit(tree)
        assert ("module.test.A", "module.test.B") in graph.graph.edges

    def test_visit_imported_base_class(self):
        tree = ast.parse(test_visit_imported_base_class_source_code)
        graph = ClassGraph()
        visitor = ClassVisitor(graph, "module.test")
        visitor.visit(tree)
        assert ("other.module.BaseClass", "module.test.Derived") in graph.graph.edges

    def test_resolve_full_name(self):
        tree = ast.parse(test_resolve_full_name_source_code)
        graph = ClassGraph()
        visitor = ClassVisitor(graph, "module.test")
        visitor.visit(tree)
        assert ("other.module.BaseClass", "module.test.Derived") in graph.graph.edges
