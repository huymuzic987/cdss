"""Behavioral tests for the opt-in medicine catalog caching layer."""

from __future__ import annotations

from collections.abc import Sequence

from cdss.domain.decision_tree.medicine_catalog import Medicine
from cdss.infrastructure.db.caching_medicine_repository import (
    CachingMedicineRepository,
    MedicineCatalogCache,
)

_LOSARTAN = Medicine(
    drug_id="DRUG0023",
    name="Losartan",
    drug_class="A",
    subgroup="ARB",
    route="Thuốc Uống",
    dose_low="25 mg",
    dose_usual="50 - 100 mg",
    dose_max="100 mg",
    source="Bảng 10",
    link=None,
    available=True,
)


class CountingRepository:
    """Repository stub that records every list_all() load."""

    def __init__(self, medicines: Sequence[Medicine]) -> None:
        self._medicines = medicines
        self.calls: int = 0

    def get_by_id(self, drug_id: str) -> Medicine | None:
        raise NotImplementedError

    def list_by_class(self, drug_class: str) -> Sequence[Medicine]:
        raise NotImplementedError

    def list_all(self) -> Sequence[Medicine]:
        self.calls += 1
        return self._medicines


def test_cache_loads_the_catalog_once_across_repository_instances() -> None:
    cache = MedicineCatalogCache()

    first = CountingRepository([_LOSARTAN])
    assert CachingMedicineRepository(first, cache).get_by_id("DRUG0023") is _LOSARTAN

    # A later request builds a fresh inner repository (new session) but shares
    # the process cache: no second DB load.
    second = CountingRepository([_LOSARTAN])
    assert CachingMedicineRepository(second, cache).list_by_class("A") == (_LOSARTAN,)

    assert first.calls == 1
    assert second.calls == 0


def test_get_by_id_and_list_by_class_share_one_load() -> None:
    cache = MedicineCatalogCache()
    inner = CountingRepository([_LOSARTAN])
    repository = CachingMedicineRepository(inner, cache)

    repository.get_by_id("DRUG0023")
    repository.list_by_class("A")

    assert inner.calls == 1


def test_unknown_id_and_class_return_empty_without_raising() -> None:
    cache = MedicineCatalogCache()
    repository = CachingMedicineRepository(CountingRepository([_LOSARTAN]), cache)

    assert repository.get_by_id("MISSING") is None
    assert repository.list_by_class("Z") == ()


def test_clear_forces_reload() -> None:
    cache = MedicineCatalogCache()
    inner = CountingRepository([_LOSARTAN])
    repository = CachingMedicineRepository(inner, cache)

    repository.get_by_id("DRUG0023")
    cache.clear()
    repository.get_by_id("DRUG0023")

    assert inner.calls == 2
