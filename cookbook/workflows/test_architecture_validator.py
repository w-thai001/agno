"""
Comprehensive test suite for Architecture Validator FSA.

Tests cover:
1. Layering validation
2. Dependency rules enforcement
3. SOLID principles checking
4. Architectural smell detection
5. Cohesion and coupling analysis
6. Architecture conformance checking
7. Cyclic dependency detection
8. Pattern detection
9. Architecture metrics computation
10. Architecture drift detection
"""

import ast
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from architecture_validator import (
    ArchitecturalPattern,
    ArchitecturalSmell,
    ArchitectureMetrics,
    ArchitectureSpec,
    ArchitectureValidator,
    Component,
    ConformanceReport,
    CouplingMatrix,
    DependencyGraph,
    DependencyRules,
    DetectedPattern,
    DriftReport,
    LayerSpec,
    LayeringReport,
    ProjectStructure,
    RuleViolations,
    SmellType,
    SOLIDReport,
    ViolationSeverity,
)


class TestLayeringValidation:
    """Test layering validation functionality."""

    def test_valid_layering(self):
        """Test validation of correct layering structure."""
        # Create project structure with valid layering
        project = ProjectStructure(root=Path("/test"))

        # Presentation layer component
        pres_comp = Component(
            name="presentation/controller.py",
            path=Path("/test/presentation/controller.py"),
            layer="presentation",
            dependencies={"business_service"}
        )

        # Business layer component
        bus_comp = Component(
            name="business/service.py",
            path=Path("/test/business/service.py"),
            layer="business",
            dependencies={"data_repository"}
        )

        # Data layer component
        data_comp = Component(
            name="data/repository.py",
            path=Path("/test/data/repository.py"),
            layer="data",
            dependencies=set()
        )

        project.components = [pres_comp, bus_comp, data_comp]

        # Build dependency graph
        project.dependency_graph.add_edge(pres_comp.name, bus_comp.name)
        project.dependency_graph.add_edge(bus_comp.name, data_comp.name)

        # Create layer spec
        layers = LayerSpec(
            layers={
                'presentation': ['business'],
                'business': ['data'],
                'data': []
            }
        )

        # Validate
        validator = ArchitectureValidator()
        report = validator.validate_layering(project, layers)

        assert report.valid is True
        assert len(report.layer_violations) == 0
        assert len(report.skip_layer_deps) == 0

    def test_skip_layer_violation(self):
        """Test detection of skip-layer dependencies."""
        project = ProjectStructure(root=Path("/test"))

        # Presentation directly depends on data (skipping business)
        pres_comp = Component(
            name="presentation/controller.py",
            path=Path("/test/presentation/controller.py"),
            layer="presentation",
            dependencies={"data_repository"}
        )

        data_comp = Component(
            name="data/repository.py",
            path=Path("/test/data/repository.py"),
            layer="data",
            dependencies=set()
        )

        project.components = [pres_comp, data_comp]
        project.dependency_graph.add_edge(pres_comp.name, data_comp.name)

        layers = LayerSpec()
        validator = ArchitectureValidator()
        report = validator.validate_layering(project, layers)

        assert report.valid is False
        assert len(report.skip_layer_deps) > 0


class TestDependencyRules:
    """Test dependency constraint validation."""

    def test_allowed_dependencies(self):
        """Test validation of allowed dependencies."""
        graph = DependencyGraph()
        graph.add_edge("module_a", "module_b")
        graph.add_edge("module_a", "module_c")

        rules = DependencyRules(
            allowed={
                "module_a": ["module_b", "module_c"],
                "module_b": [],
                "module_c": []
            }
        )

        validator = ArchitectureValidator()
        violations = validator.check_dependency_rules(graph, rules)

        assert len(violations.violated_rules) == 0

    def test_forbidden_dependencies(self):
        """Test detection of forbidden dependencies."""
        graph = DependencyGraph()
        graph.add_edge("domain", "infrastructure")  # Forbidden

        rules = DependencyRules(
            forbidden=[("domain", "infrastructure")]
        )

        validator = ArchitectureValidator()
        violations = validator.check_dependency_rules(graph, rules)

        assert len(violations.violated_rules) > 0
        assert violations.severity == ViolationSeverity.CRITICAL
        assert "domain" in violations.affected_modules

    def test_dependency_not_in_allowed_list(self):
        """Test detection of dependencies not in allowed list."""
        graph = DependencyGraph()
        graph.add_edge("module_a", "module_x")  # Not in allowed list

        rules = DependencyRules(
            allowed={
                "module_a": ["module_b", "module_c"]
            }
        )

        validator = ArchitectureValidator()
        violations = validator.check_dependency_rules(graph, rules)

        assert len(violations.violated_rules) > 0


class TestSOLIDPrinciples:
    """Test SOLID principles validation."""

    def test_srp_violation_detection(self):
        """Test detection of Single Responsibility Principle violations."""
        code = dedent("""
        class GodClass:
            def method1(self): pass
            def method2(self): pass
            def method3(self): pass
            def method4(self): pass
            def method5(self): pass
            def method6(self): pass
            def method7(self): pass
            def method8(self): pass
            def method9(self): pass
            def method10(self): pass
            def method11(self): pass
            def method12(self): pass
            def method13(self): pass
            def method14(self): pass
            def method15(self): pass
            def method16(self): pass
        """)

        tree = ast.parse(code)
        validator = ArchitectureValidator()
        report = validator.validate_solid_principles(tree)

        assert len(report.srp_violations) > 0
        assert report.srp_violations[0].principle == "SRP"

    def test_isp_violation_detection(self):
        """Test detection of Interface Segregation Principle violations."""
        code = dedent("""
        class FatInterface:
            def method1(self): pass
            def method2(self): pass
            def method3(self): pass
            def method4(self): pass
            def method5(self): pass
            def method6(self): pass
            def method7(self): pass
            def method8(self): pass
            def method9(self): pass
            def method10(self): pass
            def method11(self): pass
        """)

        tree = ast.parse(code)
        validator = ArchitectureValidator()
        report = validator.validate_solid_principles(tree)

        assert len(report.isp_violations) > 0

    def test_dip_violation_detection(self):
        """Test detection of Dependency Inversion Principle violations."""
        code = dedent("""
        class ServiceClass:
            def process(self):
                # Direct instantiation of concrete class
                concrete = ConcreteImplementation()
                return concrete.execute()
        """)

        tree = ast.parse(code)
        validator = ArchitectureValidator()
        report = validator.validate_solid_principles(tree)

        # Should detect direct instantiation
        assert len(report.dip_violations) > 0


class TestArchitecturalSmells:
    """Test architectural smell detection."""

    def test_god_component_detection_by_size(self):
        """Test detection of god components based on size."""
        project = ProjectStructure(root=Path("/test"))

        large_comp = Component(
            name="god_component.py",
            path=Path("/test/god_component.py"),
            size=600,  # Exceeds max_component_size of 500
            dependencies=set()
        )

        project.components = [large_comp]

        spec = ArchitectureSpec(max_component_size=500)
        validator = ArchitectureValidator(spec)
        smells = validator.detect_architectural_smells(project)

        god_smells = [s for s in smells if s.smell_type == SmellType.GOD_COMPONENT]
        assert len(god_smells) > 0
        assert god_smells[0].severity == ViolationSeverity.HIGH

    def test_god_component_detection_by_dependencies(self):
        """Test detection of god components based on dependency count."""
        project = ProjectStructure(root=Path("/test"))

        coupled_comp = Component(
            name="coupled_component.py",
            path=Path("/test/coupled_component.py"),
            size=100,
            dependencies={"dep1", "dep2", "dep3", "dep4", "dep5",
                         "dep6", "dep7", "dep8", "dep9", "dep10", "dep11"}
        )

        project.components = [coupled_comp]

        spec = ArchitectureSpec(max_dependencies=10)
        validator = ArchitectureValidator(spec)
        smells = validator.detect_architectural_smells(project)

        god_smells = [s for s in smells if s.smell_type == SmellType.GOD_COMPONENT]
        assert len(god_smells) > 0

    def test_feature_envy_detection(self):
        """Test detection of feature envy smell."""
        project = ProjectStructure(root=Path("/test"))

        # Component with high efferent coupling
        envious_comp = Component(
            name="envious.py",
            path=Path("/test/envious.py"),
            size=100,
            dependencies={"dep1", "dep2", "dep3", "dep4", "dep5",
                         "dep6", "dep7", "dep8", "dep9"}
        )

        project.components = [envious_comp]

        validator = ArchitectureValidator()
        smells = validator.detect_architectural_smells(project)

        envy_smells = [s for s in smells if s.smell_type == SmellType.FEATURE_ENVY]
        assert len(envy_smells) > 0


class TestCyclicDependencies:
    """Test cyclic dependency detection."""

    def test_simple_cycle_detection(self):
        """Test detection of simple A -> B -> A cycle."""
        graph = DependencyGraph()
        graph.add_edge("module_a", "module_b")
        graph.add_edge("module_b", "module_a")

        validator = ArchitectureValidator()
        cycles = validator.detect_cyclic_dependencies(graph)

        assert len(cycles) > 0
        # Should find the cycle
        cycle = cycles[0]
        assert set(cycle) == {"module_a", "module_b"}

    def test_complex_cycle_detection(self):
        """Test detection of complex A -> B -> C -> A cycle."""
        graph = DependencyGraph()
        graph.add_edge("module_a", "module_b")
        graph.add_edge("module_b", "module_c")
        graph.add_edge("module_c", "module_a")

        validator = ArchitectureValidator()
        cycles = validator.detect_cyclic_dependencies(graph)

        assert len(cycles) > 0
        cycle = cycles[0]
        assert len(cycle) == 3

    def test_no_cycle_detection(self):
        """Test that acyclic graphs return no cycles."""
        graph = DependencyGraph()
        graph.add_edge("module_a", "module_b")
        graph.add_edge("module_b", "module_c")
        graph.add_edge("module_a", "module_c")

        validator = ArchitectureValidator()
        cycles = validator.detect_cyclic_dependencies(graph)

        assert len(cycles) == 0


class TestCohesionCoupling:
    """Test cohesion and coupling analysis."""

    def test_cohesion_analysis(self):
        """Test component cohesion analysis."""
        component = Component(
            name="test_component.py",
            path=Path("/test/test_component.py"),
            methods=["method1", "method2", "get_attr1"],
            attributes=["attr1", "attr2"]
        )

        validator = ArchitectureValidator()
        cohesion = validator.analyze_component_cohesion(component)

        assert 0.0 <= cohesion.score <= 1.0
        assert 0.0 <= cohesion.lcom <= 1.0

    def test_coupling_analysis(self):
        """Test component coupling analysis."""
        comp_a = Component(
            name="module_a.py",
            path=Path("/test/module_a.py"),
            dependencies={"module_b", "module_c"}
        )

        comp_b = Component(
            name="module_b.py",
            path=Path("/test/module_b.py"),
            dependencies={"module_c"}
        )

        comp_c = Component(
            name="module_c.py",
            path=Path("/test/module_c.py"),
            dependencies=set()
        )

        validator = ArchitectureValidator()
        coupling = validator.analyze_component_coupling([comp_a, comp_b, comp_c])

        # Check efferent coupling
        assert coupling.efferent_coupling["module_a.py"] == 2
        assert coupling.efferent_coupling["module_b.py"] == 1
        assert coupling.efferent_coupling["module_c.py"] == 0

        # Check instability exists
        assert "module_a.py" in coupling.instability
        assert 0.0 <= coupling.instability["module_a.py"] <= 1.0


class TestArchitectureConformance:
    """Test architecture conformance checking."""

    def test_perfect_conformance(self):
        """Test perfect conformance to intended architecture."""
        actual = ProjectStructure(root=Path("/test"))
        actual.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies={"module_b.py"}),
            Component(name="module_b.py", path=Path("/test/module_b.py"), dependencies=set())
        ]

        intended_components = ["module_a.py", "module_b.py"]
        intended_deps = {
            "module_a.py": ["module_b.py"],
            "module_b.py": []
        }

        validator = ArchitectureValidator()
        report = validator.check_architecture_conformance(
            actual, intended_components, intended_deps
        )

        assert report.conformance_percentage > 90.0
        assert len(report.missing_components) == 0
        assert len(report.extra_components) == 0

    def test_missing_components(self):
        """Test detection of missing components."""
        actual = ProjectStructure(root=Path("/test"))
        actual.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set())
        ]

        intended_components = ["module_a.py", "module_b.py", "module_c.py"]
        intended_deps = {}

        validator = ArchitectureValidator()
        report = validator.check_architecture_conformance(
            actual, intended_components, intended_deps
        )

        assert len(report.missing_components) == 2
        assert "module_b.py" in report.missing_components
        assert "module_c.py" in report.missing_components

    def test_extra_components(self):
        """Test detection of extra components."""
        actual = ProjectStructure(root=Path("/test"))
        actual.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set()),
            Component(name="module_extra.py", path=Path("/test/module_extra.py"), dependencies=set())
        ]

        intended_components = ["module_a.py"]
        intended_deps = {}

        validator = ArchitectureValidator()
        report = validator.check_architecture_conformance(
            actual, intended_components, intended_deps
        )

        assert len(report.extra_components) > 0
        assert "module_extra.py" in report.extra_components


class TestPatternDetection:
    """Test architectural pattern detection."""

    def test_layered_pattern_detection(self):
        """Test detection of layered architecture pattern."""
        project = ProjectStructure(root=Path("/test"))
        project.components = [
            Component(name="presentation/view.py", path=Path("/test/presentation/view.py"), layer="presentation"),
            Component(name="business/service.py", path=Path("/test/business/service.py"), layer="business"),
            Component(name="data/repository.py", path=Path("/test/data/repository.py"), layer="data")
        ]

        validator = ArchitectureValidator()
        pattern = validator.detect_architecture_pattern(project)

        assert pattern.pattern_type == ArchitecturalPattern.LAYERED
        assert pattern.confidence > 0.5

    def test_mvc_pattern_detection(self):
        """Test detection of MVC pattern."""
        project = ProjectStructure(root=Path("/test"))
        project.components = [
            Component(name="model/user.py", path=Path("/test/model/user.py")),
            Component(name="view/user_view.py", path=Path("/test/view/user_view.py")),
            Component(name="controller/user_controller.py", path=Path("/test/controller/user_controller.py"))
        ]

        validator = ArchitectureValidator()
        pattern = validator.detect_architecture_pattern(project)

        assert pattern.pattern_type == ArchitecturalPattern.MVC
        assert pattern.confidence > 0.5

    def test_unknown_pattern_detection(self):
        """Test detection when no clear pattern exists."""
        project = ProjectStructure(root=Path("/test"))
        project.components = [
            Component(name="random/file1.py", path=Path("/test/random/file1.py")),
            Component(name="random/file2.py", path=Path("/test/random/file2.py"))
        ]

        validator = ArchitectureValidator()
        pattern = validator.detect_architecture_pattern(project)

        # Should return unknown or low confidence
        assert pattern.confidence < 0.5 or pattern.pattern_type == ArchitecturalPattern.UNKNOWN


class TestArchitectureMetrics:
    """Test architecture metrics computation."""

    def test_metrics_calculation(self):
        """Test calculation of architecture metrics."""
        project = ProjectStructure(root=Path("/test"))
        project.components = [
            Component(
                name="module_a.py",
                path=Path("/test/module_a.py"),
                size=100,
                complexity=5,
                dependencies={"module_b"}
            ),
            Component(
                name="module_b.py",
                path=Path("/test/module_b.py"),
                size=150,
                complexity=3,
                dependencies=set()
            )
        ]

        spec = ArchitectureSpec(max_component_size=500)
        validator = ArchitectureValidator(spec)
        metrics = validator.compute_architecture_metrics(project)

        assert isinstance(metrics, ArchitectureMetrics)
        assert 0.0 <= metrics.modularity <= 1.0
        assert 0.0 <= metrics.maintainability <= 1.0
        assert 0.0 <= metrics.testability <= 1.0
        assert 0.0 <= metrics.complexity <= 1.0
        assert 0.0 <= metrics.abstractness <= 1.0
        assert 0.0 <= metrics.distance_from_main_sequence <= 1.0

    def test_high_modularity(self):
        """Test that properly sized components result in high modularity."""
        project = ProjectStructure(root=Path("/test"))
        # All components under size threshold
        project.components = [
            Component(name=f"module_{i}.py", path=Path(f"/test/module_{i}.py"), size=100, complexity=2)
            for i in range(5)
        ]

        spec = ArchitectureSpec(max_component_size=500)
        validator = ArchitectureValidator(spec)
        metrics = validator.compute_architecture_metrics(project)

        assert metrics.modularity == 1.0  # All components are well-sized


class TestArchitectureDrift:
    """Test architecture drift detection."""

    def test_component_additions(self):
        """Test detection of added components."""
        baseline = ProjectStructure(root=Path("/test"))
        baseline.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set())
        ]

        current = ProjectStructure(root=Path("/test"))
        current.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set()),
            Component(name="module_b.py", path=Path("/test/module_b.py"), dependencies=set())
        ]

        validator = ArchitectureValidator()
        drift = validator.detect_architecture_drift(current, baseline)

        assert len(drift.components_added) == 1
        assert "module_b.py" in drift.components_added
        assert drift.drift_magnitude > 0.0

    def test_component_removals(self):
        """Test detection of removed components."""
        baseline = ProjectStructure(root=Path("/test"))
        baseline.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set()),
            Component(name="module_b.py", path=Path("/test/module_b.py"), dependencies=set())
        ]

        current = ProjectStructure(root=Path("/test"))
        current.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set())
        ]

        validator = ArchitectureValidator()
        drift = validator.detect_architecture_drift(current, baseline)

        assert len(drift.components_removed) == 1
        assert "module_b.py" in drift.components_removed

    def test_dependency_changes(self):
        """Test detection of dependency changes."""
        baseline = ProjectStructure(root=Path("/test"))
        baseline.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies={"module_b"}),
            Component(name="module_b.py", path=Path("/test/module_b.py"), dependencies=set())
        ]

        current = ProjectStructure(root=Path("/test"))
        current.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies={"module_c"}),
            Component(name="module_b.py", path=Path("/test/module_b.py"), dependencies=set())
        ]

        validator = ArchitectureValidator()
        drift = validator.detect_architecture_drift(current, baseline)

        assert len(drift.dependencies_added) > 0 or len(drift.dependencies_removed) > 0

    def test_no_drift(self):
        """Test that identical architectures show no drift."""
        baseline = ProjectStructure(root=Path("/test"))
        baseline.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set())
        ]

        current = ProjectStructure(root=Path("/test"))
        current.components = [
            Component(name="module_a.py", path=Path("/test/module_a.py"), dependencies=set())
        ]

        validator = ArchitectureValidator()
        drift = validator.detect_architecture_drift(current, baseline)

        assert drift.drift_magnitude == 0.0
        assert len(drift.components_added) == 0
        assert len(drift.components_removed) == 0


class TestCompleteValidation:
    """Test complete validation workflow."""

    def test_complete_validation_with_temp_project(self):
        """Test complete validation on a temporary project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Create a simple project structure
            (project_path / "presentation").mkdir()
            (project_path / "business").mkdir()
            (project_path / "data").mkdir()

            # Create some Python files
            (project_path / "presentation" / "controller.py").write_text(
                "from business import service\n\nclass Controller:\n    pass\n"
            )
            (project_path / "business" / "service.py").write_text(
                "from data import repository\n\nclass Service:\n    pass\n"
            )
            (project_path / "data" / "repository.py").write_text(
                "class Repository:\n    pass\n"
            )

            # Create specification
            spec = ArchitectureSpec(
                patterns=[ArchitecturalPattern.LAYERED],
                layers=LayerSpec(),
                enforce_solid=True,
                max_component_size=500
            )

            # Validate
            validator = ArchitectureValidator(spec)
            report = validator.validate(project_path, spec)

            # Check report structure
            assert isinstance(report, ValidationReport)
            assert report.conformance_score >= 0.0
            assert report.metrics is not None
            assert isinstance(report.recommendations, list)

    def test_validation_error_handling(self):
        """Test that validation handles errors gracefully."""
        spec = ArchitectureSpec()
        validator = ArchitectureValidator(spec)

        # Try to validate non-existent path
        non_existent = Path("/non/existent/path")
        report = validator.validate(non_existent, spec)

        # Should return report with error, not crash
        assert isinstance(report, ValidationReport)
        assert report.conformance_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
