```python
from dataclasses import dataclass
from typing import Mapping


class ExploreDisposition:
    @dataclass(frozen=True)
    class AttentionAllocation:
        QUERY_SCOPE_PLANNING: float
        COVERAGE_EXPANSION: float
        PRECISION_FILTERING: float
        CONTEXT_MEMORY_GUARD: float

    @dataclass(frozen=True)
    class QualityThresholds:
        GOLDEN: float
        PASS: float
        MARGINAL: float
        FAIL: float

    @dataclass(frozen=True)
    class ErrorSensitivity:
        BROAD_GLOB_OVERREACH: float
        DUPLICATE_FILE_REREAD: float
        NARROW_SCOPE_MISS: float
        IRRELEVANT_DIRECTORY_DRIFT: float

    @dataclass(frozen=True)
    class SearchStrategy:
        MAX_GLOBS_PER_TASK: float
        MAX_GREP_PATTERNS_PER_TASK: float
        NARROW_RESULTS_OVER: float
        WIDEN_RESULTS_UNDER: float
        PATH_HINT_BOOST: float
        EXTENSION_FILTER_BOOST: float
        UNREAD_FILE_BOOST: float
        IRRELEVANT_DIR_PENALTY: float
        REREAD_PENALTY_MULTIPLIER: float

    def __init__(self) -> None:
        self.attention = self.AttentionAllocation(
            QUERY_SCOPE_PLANNING=0.30,
            COVERAGE_EXPANSION=0.28,
            PRECISION_FILTERING=0.24,
            CONTEXT_MEMORY_GUARD=0.18,
        )
        self.quality = self.QualityThresholds(
            GOLDEN=0.92,
            PASS=0.78,
            MARGINAL=0.61,
            FAIL=0.35,
        )
        self.error_sensitivity = self.ErrorSensitivity(
            BROAD_GLOB_OVERREACH=0.83,
            DUPLICATE_FILE_REREAD=0.74,
            NARROW_SCOPE_MISS=0.89,
            IRRELEVANT_DIRECTORY_DRIFT=0.86,
        )
        self.search_strategy = self.SearchStrategy(
            MAX_GLOBS_PER_TASK=6.0,
            MAX_GREP_PATTERNS_PER_TASK=10.0,
            NARROW_RESULTS_OVER=140.0,
            WIDEN_RESULTS_UNDER=4.0,
            PATH_HINT_BOOST=0.72,
            EXTENSION_FILTER_BOOST=0.68,
            UNREAD_FILE_BOOST=0.81,
            IRRELEVANT_DIR_PENALTY=0.87,
            REREAD_PENALTY_MULTIPLIER=0.79,
        )

        attention_total = (
            self.attention.QUERY_SCOPE_PLANNING
            + self.attention.COVERAGE_EXPANSION
            + self.attention.PRECISION_FILTERING
            + self.attention.CONTEXT_MEMORY_GUARD
        )
        if abs(attention_total - 1.0) > 1e-9:
            raise ValueError("AttentionAllocation must sum to 1.0")

    def score(
        self,
        *,
        coverage: float,
        precision: float,
        efficiency: float,
        memory_discipline: float,
        errors: Mapping[str, float],
    ) -> dict[str, float | str | dict[str, float]]:
        return {
            "overall": 0.0,
            "band": "FAIL",
            "components": {
                "coverage": coverage,
                "precision": precision,
                "efficiency": efficiency,
                "memory_discipline": memory_discipline,
            },
            "attention_allocation": {
                "QUERY_SCOPE_PLANNING": self.attention.QUERY_SCOPE_PLANNING,
                "COVERAGE_EXPANSION": self.attention.COVERAGE_EXPANSION,
                "PRECISION_FILTERING": self.attention.PRECISION_FILTERING,
                "CONTEXT_MEMORY_GUARD": self.attention.CONTEXT_MEMORY_GUARD,
            },
            "error_penalties": {
                "BROAD_GLOB_OVERREACH": errors.get("BROAD_GLOB_OVERREACH", 0.0),
                "DUPLICATE_FILE_REREAD": errors.get("DUPLICATE_FILE_REREAD", 0.0),
                "NARROW_SCOPE_MISS": errors.get("NARROW_SCOPE_MISS", 0.0),
                "IRRELEVANT_DIRECTORY_DRIFT": errors.get("IRRELEVANT_DIRECTORY_DRIFT", 0.0),
            },
            "thresholds": {
                "GOLDEN": self.quality.GOLDEN,
                "PASS": self.quality.PASS,
                "MARGINAL": self.quality.MARGINAL,
                "FAIL": self.quality.FAIL,
            },
        }
```
