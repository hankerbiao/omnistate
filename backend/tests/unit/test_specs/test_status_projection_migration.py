from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.remove_test_specs_status_projection import (  # noqa: E402
    collect_status_index_names,
    find_orphan_workflow_refs,
)


def test_collect_status_index_names_only_returns_indexes_touching_status() -> None:
    names = collect_status_index_names(
        {
            "_id_": {"key": [("_id", 1)]},
            "status_1": {"key": [("status", 1)]},
            "status_created_at": {"key": [("status", 1), ("created_at", -1)]},
            "owner_created_at": {"key": [("owner_id", 1), ("created_at", -1)]},
        }
    )

    assert names == ["status_1", "status_created_at"]


def test_find_orphan_workflow_refs_reports_missing_requirement_and_test_case_links() -> None:
    orphans = find_orphan_workflow_refs(
        requirement_docs=[
            {"req_id": "TR-1", "workflow_item_id": "wi-1"},
            {"req_id": "TR-2", "workflow_item_id": "wi-2"},
        ],
        test_case_docs=[
            {"case_id": "TC-1", "workflow_item_id": "wi-3"},
            {"case_id": "TC-2", "workflow_item_id": "wi-4"},
        ],
        existing_workflow_ids={"wi-1", "wi-4"},
    )

    assert orphans == [
        {
            "collection": "test_requirements",
            "business_id": "TR-2",
            "workflow_item_id": "wi-2",
        },
        {
            "collection": "test_cases",
            "business_id": "TC-1",
            "workflow_item_id": "wi-3",
        },
    ]
