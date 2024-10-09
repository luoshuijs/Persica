import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _ast import expr

    from persica.scanner.graph import ClassGraph


class ClassVisitor(ast.NodeVisitor):
    def __init__(self, graph: "ClassGraph", module_prefix: str):
        self.graph = graph
        self.imports: dict[str, str] = {}  # 映射本地名称到完整的模块路径
        self.module_prefix = module_prefix  # 当前模块的完整路径

    def visit_ImportFrom(self, node):
        """
        处理形如 `from module import ClassName` 的导入语句。
        """
        module = node.module  # 导入的模块，例如 'a.b.c'
        for alias in node.names:
            if alias.name == "*":
                # 对于 'from module import *'，可以根据实际需求处理
                pass
            else:
                local_name = alias.asname if alias.asname else alias.name
                full_name = f"{module}.{alias.name}"
                self.imports[local_name] = full_name
        self.generic_visit(node)

    def visit_Import(self, node):
        """
        处理形如 `import module` 或 `import module as mod` 的导入语句。
        """
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self.imports[local_name] = alias.name  # 直接存储模块的完整路径
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """
        处理类定义，提取类名、父类，并添加到 ClassGraph 中。
        """
        class_name = f"{self.module_prefix}.{node.name}"
        parent_names = set()
        for base in node.bases:
            parent_full_name = self.resolve_full_name(base)
            if parent_full_name:
                parent_names.add(parent_full_name)
        # 传递 module_path 参数到 add_class 方法
        self.graph.add_class(class_name, parent_names, self.module_prefix)
        self.generic_visit(node)

    def resolve_full_name(self, node: "expr") -> str | None:
        """
        解析父类的完整模块路径和类名。
        """
        if isinstance(node, ast.Name):
            # 直接使用的类名，检查是否为导入的别名
            name = node.id
            return self.imports.get(name, f"{self.module_prefix}.{name}")
        if isinstance(node, ast.Attribute):
            # 处理形如 module.ClassName 的父类
            names = []
            while isinstance(node, ast.Attribute):
                names.insert(0, node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                names.insert(0, node.id)
                base_name = names[0]
                full_name = ".".join(names)
                # 检查是否在导入的模块中
                if base_name in self.imports:
                    imported_base = self.imports[base_name]
                    full_name = ".".join([imported_base] + names[1:])
                return full_name
            if isinstance(node, ast.Call):
                # 处理泛型类型，例如 `List[int]`
                return self.resolve_full_name(node.func)
        elif isinstance(node, ast.Subscript):
            # 处理带有下标的类型，例如 `List[int]`
            return self.resolve_full_name(node.value)
        return None  # 其他情况返回 None
