import ast
from pathlib import Path
from typing import Iterator, Optional

from networkx import NetworkXError

from persica.scanner.graph import ClassGraph
from persica.scanner.visitor import ClassVisitor


class ClassPathScanner:
    def __init__(self, default_directory: Optional[str] = None):
        self.class_graph = ClassGraph()
        self.default_directory = default_directory

    def flash(self, directory: Optional[str] = None):
        directory = directory or self.default_directory
        if directory is not None:
            self.parse_directory(directory)

    def parse_directory(self, directory):
        path = Path(directory)
        for file_path in path.rglob("*.py"):
            module_prefix = file_path.with_suffix("").as_posix().replace("/", ".")  # 转换文件路径为模块前缀
            visitor = ClassVisitor(self.class_graph, module_prefix)
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            tree = ast.parse(content, filename=file_path)
            visitor.visit(tree)

    def get_module(self, superclass_name: str) -> Iterator[str]:
        try:
            all_descendants = self.class_graph.find_all_descendants(superclass_name)
            for full_class_path in all_descendants:
                module_path, _ = full_class_path.rsplit(".", 1)
                yield module_path
        except NetworkXError:
            pass
