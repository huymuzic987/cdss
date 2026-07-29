"""Context-patch domain error construction."""

from typing import Any

from cdss.domain.decision_tree.contracts import RunState
from cdss.domain.decision_tree.errors import ContextPatchError


def patch_error(
    run_state: RunState,
    *,
    tree_key: str | None,
    node_key: str | None,
    reason: str,
    **details: Any,
) -> ContextPatchError:
    return ContextPatchError(
        tree_key=tree_key,
        node_key=node_key,
        details={"reason": reason, **details},
        partial_run_state=run_state,
    )
