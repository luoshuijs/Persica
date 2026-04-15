from persica.scanner.path import ClassPathScanner


class TestScannerRoots:
    def test_flash_scans_package_root_init_module(self):
        scanner = ClassPathScanner(default_base_packages=["tests.sample_package_init"])

        scanner.flash()

        graph = scanner.class_graph
        assert "tests.sample_package_init" in scanner.scanned_modules
        assert "tests.sample_package_init.PackageRootBase" in graph.graph.nodes
        assert (
            "tests.sample_package_init.PackageRootBase",
            "tests.sample_package_init.PackageRootChild",
        ) in graph.graph.edges

    def test_flash_scans_direct_module_target(self):
        scanner = ClassPathScanner(default_base_packages=["tests.sample_module"])

        scanner.flash()

        graph = scanner.class_graph
        assert scanner.scanned_modules == ["tests.sample_module"]
        assert "tests.sample_module.DirectModuleBase" in graph.graph.nodes
        assert ("tests.sample_module.DirectModuleBase", "tests.sample_module.DirectModuleChild") in graph.graph.edges

    def test_flash_resolves_relative_import_edges(self):
        scanner = ClassPathScanner(default_base_packages=["tests.sample_relative_package"])

        scanner.flash()

        assert "tests.sample_relative_package.base" in scanner.scanned_modules
        assert "tests.sample_relative_package.child" in scanner.scanned_modules
        assert (
            "tests.sample_relative_package.base.RelativeBase",
            "tests.sample_relative_package.child.RelativeChild",
        ) in scanner.class_graph.graph.edges

    def test_flash_scans_namespace_package_root(self):
        scanner = ClassPathScanner(default_base_packages=["sample_namespace_package"])

        scanner.flash()

        assert "sample_namespace_package.child_module" in scanner.scanned_modules
        assert "sample_namespace_package.child_module.NamespaceBase" in scanner.class_graph.graph.nodes
        assert (
            "sample_namespace_package.child_module.NamespaceBase",
            "sample_namespace_package.child_module.NamespaceChild",
        ) in scanner.class_graph.graph.edges
