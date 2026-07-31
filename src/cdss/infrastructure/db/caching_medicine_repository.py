"""Optional process-level caching layer for the immutable medicine catalog.

The medicine catalog is small, read-heavy reference data (see
caching_repository.py's TreeGraphCache for the identical rationale and
staleness tradeoff). This cache is **opt-in** (``CDSS_MEDICINE_CACHE_ENABLED``)
and defaults to off; a deployment that enables it owns invalidation via
``MedicineCatalogCache.clear()`` after any re-seed of the ``medicines`` table.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache

from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository


class MedicineCatalogCache:
    """Process-lifetime store of the full, successfully loaded medicine catalog."""

    def __init__(self) -> None:
        self._by_id: dict[str, Medicine] | None = None
        self._by_class: dict[str, tuple[Medicine, ...]] | None = None

    def get_or_load(
        self, loader: Callable[[], Sequence[Medicine]]
    ) -> tuple[dict[str, Medicine], dict[str, tuple[Medicine, ...]]]:
        if self._by_id is not None and self._by_class is not None:
            return self._by_id, self._by_class

        # Load outside any lock: the loader may raise, which must propagate
        # and must not be cached so a later seed is picked up.
        medicines = loader()
        by_id = {medicine.drug_id: medicine for medicine in medicines}
        by_class: dict[str, list[Medicine]] = {}
        for medicine in medicines:
            if medicine.drug_class is not None:
                by_class.setdefault(medicine.drug_class, []).append(medicine)

        self._by_id = by_id
        self._by_class = {class_letter: tuple(group) for class_letter, group in by_class.items()}
        return self._by_id, self._by_class

    def clear(self) -> None:
        self._by_id = None
        self._by_class = None


class CachingMedicineRepository(MedicineRepository):
    """Wrap a repository, serving the medicine catalog from a shared cache."""

    def __init__(self, inner: MedicineRepository, cache: MedicineCatalogCache) -> None:
        self._inner = inner
        self._cache = cache

    def get_by_id(self, drug_id: str) -> Medicine | None:
        by_id, _ = self._cache.get_or_load(self._inner.list_all)
        return by_id.get(drug_id)

    def list_by_class(self, drug_class: str) -> Sequence[Medicine]:
        _, by_class = self._cache.get_or_load(self._inner.list_all)
        return by_class.get(drug_class, ())

    def list_all(self) -> Sequence[Medicine]:
        return self._inner.list_all()


@lru_cache(maxsize=1)
def get_medicine_catalog_cache() -> MedicineCatalogCache:
    """Return the process-wide medicine catalog cache (one instance per process)."""

    return MedicineCatalogCache()
