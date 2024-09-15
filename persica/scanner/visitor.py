import ast

from persica.scanner.graph import ClassGraph


class ClassVisitor(ast.NodeVisitor):
    def __init__(self, graph: ClassGraph, module_prefix):
        self.graph = graph
        self.imports = {}
        self.module_prefix = module_prefix

    def visit_ImportFrom(self, node):
        # 处理形如 `from module import ClassName` 的导入
        module = node.module
        for alias in node.names:
            self.imports[alias.name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_Import(self, node):
        # 处理形如 `import module.ClassName` 的导入
        for alias in node.names:
            self.imports[alias.name] = alias.asname if alias.asname else alias.name
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_name = f"{self.module_prefix}.{node.name}"
        parent_names = set()
        for parent in node.bases:
            if isinstance(parent, ast.Name):
                # 直接使用的类名，检查是否为导入的别名
                parent_name = self.imports.get(parent.id, parent.id)
                parent_names.add(parent_name)
            elif isinstance(parent, ast.Attribute):
                # 处理形如 module.ClassName 的父类
                if isinstance(parent.value, ast.Name):
                    parent_names.add(f"{parent.value.id}.{parent.attr}")

        self.graph.add_class(class_name, parent_names)
        self.generic_visit(node)
