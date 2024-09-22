from persica.scanner.path import ClassPathScanner


class TestPathScanner:
    def test_flash_with_test_package(self):
        scanner = ClassPathScanner(default_base_packages=["tests.test_package"])
        scanner.flash()
        graph = scanner.class_graph

        # 预期的类名列表
        expected_classes = {
            "tests.test_package.module_a.BaseClass",
            "tests.test_package.module_a.DerivedClass",
            "tests.test_package.subpackage.module_b.AnotherDerivedClass",
        }

        # 检查类是否被正确添加到图中
        assert expected_classes.issubset(set(graph.graph.nodes))

        # 检查继承关系（边）
        assert (
            "tests.test_package.module_a.BaseClass",
            "tests.test_package.module_a.DerivedClass",
        ) in graph.graph.edges
        assert (
            "tests.test_package.module_a.DerivedClass",
            "tests.test_package.subpackage.module_b.AnotherDerivedClass",
        ) in graph.graph.edges

    def test_get_modules_to_import_existing_class(self):
        scanner = ClassPathScanner(default_base_packages=["tests.test_package"])
        scanner.flash()
        modules = scanner.get_modules_to_import("tests.test_package.module_a.BaseClass")
        expected_modules = {"tests.test_package.module_a", "tests.test_package.subpackage.module_b"}
        assert expected_modules == modules
