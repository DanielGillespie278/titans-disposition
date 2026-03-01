```python
from __future__ import annotations


class GeneralPurposeDisposition:
    class AttentionAllocation:
        def __init__(self) -> None:
            self.task_alignment: float = 0.28
            self.read_before_write: float = 0.18
            self.tool_safety: float = 0.20
            self.leader_sync: float = 0.12
            self.concise_delivery: float = 0.10
            self.citation_traceability: float = 0.12

        def as_dict(self) -> dict[str, float]:
            return {
                "task_alignment": self.task_alignment,
                "read_before_write": self.read_before_write,
                "tool_safety": self.tool_safety,
                "leader_sync": self.leader_sync,
                "concise_delivery": self.concise_delivery,
                "citation_traceability": self.citation_traceability,
            }

    class QualityThresholds:
        def __init__(self) -> None:
            self.GOLDEN: float = 0.92
            self.PASS: float = 0.78
            self.MARGINAL: float = 0.62
            self.FAIL: float = 0.35

        def as_dict(self) -> dict[str, float]:
            return {
                "GOLDEN": self.GOLDEN,
                "PASS": self.PASS,
                "MARGINAL": self.MARGINAL,
                "FAIL": self.FAIL,
            }

    class ErrorSensitivity:
        def __init__(self) -> None:
            self.scope_creep_beyond_task: float = 0.86
            self.edit_without_reading_file: float = 0.90
            self.destructive_bash_without_confirmation: float = 0.98
            self.redo_completed_leader_work: float = 0.72
            self.overly_verbose_when_concise_needed: float = 0.55
            self.missing_file_path_line_citations: float = 0.84
            self.budget_exceeded_without_justification: float = 0.90

        def as_dict(self) -> dict[str, float]:
            return {
                "scope_creep_beyond_task": self.scope_creep_beyond_task,
                "edit_without_reading_file": self.edit_without_reading_file,
                "destructive_bash_without_confirmation": self.destructive_bash_without_confirmation,
                "redo_completed_leader_work": self.redo_completed_leader_work,
                "overly_verbose_when_concise_needed": self.overly_verbose_when_concise_needed,
                "missing_file_path_line_citations": self.missing_file_path_line_citations,
                "budget_exceeded_without_justification": self.budget_exceeded_without_justification,
            }

    class ScopeGuard:
        def __init__(self) -> None:
            self.max_files_edited_per_task: int = 8
            self.max_bash_commands: int = 18

        def as_dict(self) -> dict[str, int]:
            return {
                "max_files_edited_per_task": self.max_files_edited_per_task,
                "max_bash_commands": self.max_bash_commands,
            }

    class TriageProtocol:
        """Complexity assessment before acting. Fires at task start, not during.

        The agent must classify each work item before touching any files.
        This prevents indiscriminate exploration -- the failure mode where
        a trivial assertion fix gets the same 20-call investigation as a
        complex multi-file race condition.

        Multi-category budgeting:
        When a task has multiple fixes across different root cause categories,
        budget PER CATEGORY, not one tier for the whole task:
          total = sum(budget[tier_i] * count_i for each category)
        Example: 3 trivial + 2 moderate + 1 complex = 15 + 24 + 25 = 64
        (capped at total_budget_hard_cap = 40).

        If actual calls approach 80% of estimated budget, output:
          "BUDGET CHECK: [N]/[estimate] calls used. Remaining: [items]. Adjusting."

        Hard cap monitoring:
        When total_calls >= 80% of total_budget_hard_cap (32 of 40), output:
          "HARD CAP APPROACH: [N]/40 total calls. Task-relevant: [M]. Continuing because: [reason]."
        Both checks are independent -- estimate check catches overrun vs plan,
        hard cap check catches absolute utilization regardless of estimate accuracy.
        """
        def __init__(self) -> None:
            self.assess_before_acting: bool = True
            self.budget_per_complexity: dict[str, int] = {
                "trivial": 5,     # Single assertion change, obvious fix
                "moderate": 8,    # Read source + test, 1-2 file root cause
                "complex": 15,    # Platform quirks, async races, multi-file tracing
            }
            self.multi_category_budgeting: bool = True
            self.budget_check_at_pct: float = 0.80
            self.hard_cap_warning_threshold: float = 0.80
            self.total_budget_hard_cap: int = 40
            self.budget_exceeded_action: str = "flag_and_justify"

        def as_dict(self) -> dict[str, object]:
            return {
                "assess_before_acting": self.assess_before_acting,
                "budget_per_complexity": self.budget_per_complexity,
                "multi_category_budgeting": self.multi_category_budgeting,
                "budget_check_at_pct": self.budget_check_at_pct,
                "hard_cap_warning_threshold": self.hard_cap_warning_threshold,
                "total_budget_hard_cap": self.total_budget_hard_cap,
                "budget_exceeded_action": self.budget_exceeded_action,
            }

    class CitationProtocol:
        """Structural fix for the citation capability gap.

        Weight nudges don't work because the agent doesn't know it should
        cite or how. This makes citation a structural requirement rather
        than a scored behavior.
        """
        def __init__(self) -> None:
            self.require_file_line_for_root_cause: bool = True
            self.format: str = "file_path:line_number"
            self.minimum_citations_per_fix: int = 1

        def as_dict(self) -> dict[str, object]:
            return {
                "require_file_line_for_root_cause": self.require_file_line_for_root_cause,
                "format": self.format,
                "minimum_citations_per_fix": self.minimum_citations_per_fix,
            }

    class ProductionGuard:
        """Scope boundary for test-fix tasks. Prevents production code edits.

        When a task is "fix test failures", the scope is: edit test files,
        create stubs/fixtures, update assertions. Production code is OUT
        OF SCOPE unless the test failure reveals a genuine production defect.

        Before touching any file outside tests/ or conftest.py, the agent
        must state:
          "PRODUCTION EDIT REQUIRED: [file] -- reason: [why the test failure
           cannot be fixed without modifying production code]. Callers
           verified at: [file:line]."
        If that sentence cannot be completed with verifiable citations,
        the production edit must not happen.
        """
        def __init__(self) -> None:
            self.test_task_keywords: list[str] = [
                "fix test", "test failure", "failing test", "test fix",
            ]
            self.allowed_edit_paths: list[str] = [
                "tests/", "conftest.py",
            ]
            self.allowed_stub_paths: list[str] = [
                "src/",
            ]
            self.require_justification_for_production_edit: bool = True

        def as_dict(self) -> dict[str, object]:
            return {
                "test_task_keywords": self.test_task_keywords,
                "allowed_edit_paths": self.allowed_edit_paths,
                "allowed_stub_paths": self.allowed_stub_paths,
                "require_justification_for_production_edit": self.require_justification_for_production_edit,
            }

    def __init__(self) -> None:
        self.attention_allocation = self.AttentionAllocation()
        self.quality_thresholds = self.QualityThresholds()
        self.error_sensitivity = self.ErrorSensitivity()
        self.scope_guard = self.ScopeGuard()
        self.triage_protocol = self.TriageProtocol()
        self.citation_protocol = self.CitationProtocol()
        self.production_guard = self.ProductionGuard()

    def score(self, observations: dict[str, float]) -> dict[str, object]:
        return {
            "overall_score": 0.0,
            "quality_band": "FAIL",
            "attention_score": 0.0,
            "error_penalty": 0.0,
            "checks": {
                "attention_allocation": self.attention_allocation.as_dict(),
                "quality_thresholds": self.quality_thresholds.as_dict(),
                "error_sensitivity": self.error_sensitivity.as_dict(),
                "scope_guard": self.scope_guard.as_dict(),
                "triage_protocol": self.triage_protocol.as_dict(),
                "citation_protocol": self.citation_protocol.as_dict(),
                "production_guard": self.production_guard.as_dict(),
            },
            "violations": [],
            "notes": [],
        }
```
