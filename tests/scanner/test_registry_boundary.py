from importlib import import_module

from persica.factory.abstract import AbstractAutowireCapableFactory
from persica.factory.registry import DefinitionRegistry
from persica.scanner.path import ClassPathScanner


class TestRegistryBoundary:
    def test_registry_registers_only_classes_from_scanned_modules(self):
        outside_module = import_module("tests.outside_components")
        scanned_module = import_module("tests.sample_module")

        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(default_base_packages=["tests.sample_module"])
        scanner.flash()
        registry = DefinitionRegistry(factory, scanner)

        registry.flash()

        assert outside_module.OutsideLoadedComponent not in factory.object_definitions
        assert scanned_module.ScannedModuleComponent in factory.object_definitions
        assert scanned_module.ScannedModuleFactory in factory.object_definitions
        assert factory.object_definitions[scanned_module.ScannedModuleFactory].is_factory is True

    def test_registry_skips_unrelated_broken_modules_under_scan_root(self):
        scanned_module = import_module("tests.sample_registry_root.component_module")

        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(default_base_packages=["tests.sample_registry_root"])
        scanner.flash()
        registry = DefinitionRegistry(factory, scanner)

        registry.flash()

        assert scanned_module.RootScannedComponent in factory.object_definitions
        assert registry.import_module_status["tests.sample_registry_root.component_module"] is True
        assert "tests.sample_registry_root.broken_module" not in registry.import_module_status

    def test_registry_registers_scanned_subclass_through_external_base(self):
        scanned_module = import_module("tests.sample_cross_boundary_module")

        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(default_base_packages=["tests.sample_cross_boundary_module"])
        scanner.flash()
        registry = DefinitionRegistry(factory, scanner)

        registry.flash()

        assert scanned_module.LocalCrossBoundaryComponent in factory.object_definitions
        assert registry.import_module_status["tests.sample_cross_boundary_module"] is True

    def test_registry_skips_modules_with_non_framework_external_bases(self):
        scanned_module = import_module("tests.sample_non_framework_boundary.safe_component")

        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(default_base_packages=["tests.sample_non_framework_boundary"])
        scanner.flash()
        registry = DefinitionRegistry(factory, scanner)

        registry.flash()

        assert scanned_module.SafeBoundaryComponent in factory.object_definitions
        assert "tests.sample_non_framework_boundary.broken_non_framework" not in registry.import_module_status

    def test_registry_imports_scanned_descendants_of_external_framework_seed(self):
        root_module = import_module("tests.sample_cross_boundary_chain.module_a")
        leaf_module = import_module("tests.sample_cross_boundary_chain.module_b")

        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(default_base_packages=["tests.sample_cross_boundary_chain"])
        scanner.flash()
        registry = DefinitionRegistry(factory, scanner)

        registry.flash()

        assert root_module.CrossBoundaryRootComponent in factory.object_definitions
        assert leaf_module.CrossBoundaryLeafComponent in factory.object_definitions
        assert registry.import_module_status["tests.sample_cross_boundary_chain.module_a"] is True
        assert registry.import_module_status["tests.sample_cross_boundary_chain.module_b"] is True

    def test_registry_flash_resets_import_state_between_scan_roots(self):
        factory = AbstractAutowireCapableFactory()
        scanner = ClassPathScanner(default_base_packages=[])
        registry = DefinitionRegistry(factory, scanner)

        scanner.flash(base_packages=["tests.sample_module"])
        registry.flash()

        assert registry.import_module_status == {"tests.sample_module": True}

        scanner.flash(base_packages=["tests.sample_registry_root"])
        registry.flash()

        assert registry.import_module_status == {"tests.sample_registry_root.component_module": True}
