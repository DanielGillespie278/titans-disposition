```python
class PlanDisposition:
    class AttentionAllocation:
        def __init__(self) -> None:
            self.read_actual_code_first = 0.34
            self.validate_target_files_exist = 0.20
            self.dependency_blocker_mapping = 0.16
            self.scope_control_simple_vs_complex = 0.12
            self.path_line_specificity = 0.12
            self.verification_design = 0.06

        def as_dict(self) -> dict[str, float]:
            return {
                "read_actual_code_first": self.read_actual_code_first,
                "validate_target_files_exist": self.validate_target_files_exist,
                "dependency_blocker_mapping": self.dependency_blocker_mapping,
                "scope_control_simple_vs_complex": self.scope_control_simple_vs_complex,
                "path_line_specificity": self.path_line_specificity,
                "verification_design": self.verification_design,
            }

    class QualityThresholds:
        def __init__(self) -> None:
            self.GOLDEN = 0.92
            self.PASS = 0.79
            self.MARGINAL = 0.58
            self.FAIL = 0.00

        def as_dict(self) -> dict[str, float]:
            return {
                "GOLDEN": self.GOLDEN,
                "PASS": self.PASS,
                "MARGINAL": self.MARGINAL,
                "FAIL": self.FAIL,
            }

    class ErrorSensitivity:
        def __init__(self) -> None:
            self.no_codebase_read_before_plan = 1.00
            self.references_nonexistent_files = 0.98
            self.vague_without_paths_or_lines = 0.94
            self.missing_blocking_dependencies = 0.90
            self.over_engineers_simple_task = 0.80
            self.too_many_steps_for_scope = 0.76

        def as_dict(self) -> dict[str, float]:
            return {
                "no_codebase_read_before_plan": self.no_codebase_read_before_plan,
                "references_nonexistent_files": self.references_nonexistent_files,
                "vague_without_paths_or_lines": self.vague_without_paths_or_lines,
                "missing_blocking_dependencies": self.missing_blocking_dependencies,
                "over_engineers_simple_task": self.over_engineers_simple_task,
                "too_many_steps_for_scope": self.too_many_steps_for_scope,
            }

    class PlanQuality:
        def __init__(self) -> None:
            self.max_steps_default = 6
            self.max_steps_simple = 3
            self.max_steps_complex = 9
            self.min_files_cited = 2
            self.min_line_refs = 2
            self.verification_requirements = {
                "read_code_before_planning": 1.00,
                "confirm_file_existence": 1.00,
                "include_file_paths": 1.00,
                "include_line_numbers": 0.95,
                "identify_blocking_dependencies": 0.95,
                "justify_step_count_by_scope": 0.90,
            }

        def as_dict(self) -> dict[str, object]:
            return {
                "max_steps_default": self.max_steps_default,
                "max_steps_simple": self.max_steps_simple,
                "max_steps_complex": self.max_steps_complex,
                "min_files_cited": self.min_files_cited,
                "min_line_refs": self.min_line_refs,
                "verification_requirements": self.verification_requirements,
            }

    def __init__(self) -> None:
        self.attention = self.AttentionAllocation()
        self.thresholds = self.QualityThresholds()
        self.error_sensitivity = self.ErrorSensitivity()
        self.plan_quality = self.PlanQuality()

        attention_total = sum(self.attention.as_dict().values())
        if abs(attention_total - 1.0) > 1e-9:
            raise ValueError("AttentionAllocation must sum to 1.0")

        if not (
            self.thresholds.GOLDEN
            > self.thresholds.PASS
            > self.thresholds.MARGINAL
            > self.thresholds.FAIL
        ):
            raise ValueError("Threshold ordering must satisfy GOLDEN > PASS > MARGINAL > FAIL")

    def score(self, observed: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "overall_score": 0.00,
            "quality_band": "FAIL",
            "attention_allocation": self.attention.as_dict(),
            "quality_thresholds": self.thresholds.as_dict(),
            "error_sensitivity": self.error_sensitivity.as_dict(),
            "plan_quality": self.plan_quality.as_dict(),
            "observed": observed or {},
            "violations": {},
            "gates": {
                "read_before_plan": False,
                "file_existence_verified": False,
                "paths_and_lines_present": False,
                "blocking_dependencies_mapped": False,
            },
        }
```
