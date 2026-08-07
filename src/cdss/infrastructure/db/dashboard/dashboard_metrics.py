"""Dashboard aggregate result types and ordered bucket definitions."""

from dataclasses import dataclass


@dataclass
class OverviewCounts:
    total_patients: int
    total_visits: int
    new_patients_last_30_days: int
    age_counts: dict[str, int]
    gender_counts: dict[str, int]
    comorbidity_counts: dict[str, int]
    risk_factor_counts: dict[str, int]


@dataclass
class VisitNumberAggregate:
    visit_number: int
    count: int
    bp_controlled_rate: float
    avg_sbp: float | None
    avg_dbp: float | None


@dataclass
class OutcomesCounts:
    target_counts: dict[str, int]
    by_visit_number: list[VisitNumberAggregate]
    sbp_severity_counts: dict[str, int]
    mean_sbp: float | None
    median_sbp: float | None


# Age-bucket / SBP-severity thresholds are shared between the SQL path
# (overview_counts/outcomes_counts) and the Python path (list_patients) so
# both produce identical bucket labels.
_AGE_BUCKETS = [(45, "<45"), (65, "45-64"), (75, "65-74")]
_AGE_BUCKET_LAST = "75+"
# Bucket labels don't sort into the right order alphabetically ("45-64" <
# "75+" < "<45" by string comparison) -- callers building a Count list use
# this to order rows the way the chart should read, not alphabetically.
AGE_BUCKET_ORDER = [label for _, label in _AGE_BUCKETS] + [_AGE_BUCKET_LAST, "Unknown"]

_SBP_BUCKETS = [
    (130, "SBP <130 mmHg"),
    (140, "SBP 130-139 mmHg"),
    (160, "SBP 140-159 mmHg"),
    (180, "SBP 160-179 mmHg"),
]
_SBP_BUCKET_LAST = "SBP >=180 mmHg"
SBP_BUCKET_ORDER = [label for _, label in _SBP_BUCKETS] + [_SBP_BUCKET_LAST]


def risk_factor_bucket_label(count: int) -> str:
    return str(count) if count < 5 else "5+"
