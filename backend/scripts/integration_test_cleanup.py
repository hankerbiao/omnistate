"""Shared rules and executors for integration-test junk cleanup.

Used by cleanup_test_data.py and legacy per-module cleanup scripts.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings

# ---------------------------------------------------------------------------
# Preserve lists (never delete)
# ---------------------------------------------------------------------------

PRESERVED_USER_IDS = frozenset(
    {
        "test_admin",
        "admin",
        "tpm",
        "reviewer",
        "dev",
        "qa",
        "tester",
        "integ_tpm",
        "integ_reviewer",
        "integ_dev",
        "integ_qa",
        "integ_tester",
        "integ_auto_dev",
        "integ_no_role",
    }
)

PRESERVED_ROLE_IDS = frozenset(
    {"ADMIN", "TPM", "REVIEWER", "MANUAL_DEV", "QA", "TESTER", "AUTO_DEV"}
)

PRESERVED_LAB_CODES = frozenset(
    {"DEFAULT", "BIOS", "DDR5", "BMC", "CPU", "GPU", "NET", "PWR", "STORAGE"}
)

ALL_MODULES = ("users", "permissions", "roles", "navigation", "catalog", "workflow")

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

EPHEMERAL_USER_ID_PREFIXES = (
    "test_tpm_",
    "test_reviewer_",
    "test_dev_",
    "test_qa_",
    "test_tester_",
    "test_auto_dev_",
    "test_no_role_",
    "user_test_",
    "user_user_",
)

PERM_ID_PREFIXES = ("test_perm_", "test_perm_update_")
ROLE_ID_PREFIXES = ("role_test_", "role_role_")
NAV_VIEW_PREFIXES = ("test_view_", "test_update_", "test_delete_")
JUNK_SEGMENT_NAMES = frozenset({"integration"})
JUNK_SEGMENT_PREFIXES = ("prefix_", "seg_")

LAB_NAME_PATTERNS = (
    re.compile(r"^Lab test_\d+$"),
    re.compile(r"^Mixed Case test_\d+$"),
    re.compile(r"^Updated Lab Name$"),
    re.compile(r"^First$"),
    re.compile(r"^Second$"),
    re.compile(r"^TPM Lab$"),
    re.compile(r"^Forbidden$"),
)

LAB_CODE_PATTERNS = (
    re.compile(r"^L\d{8,}$"),
    re.compile(r"^DUP[A-Z0-9]+$"),
    re.compile(r"^Mixed_test_\d+$"),
    re.compile(r"^T[A-Z0-9]{6,}$"),
    re.compile(r"^X[A-Z0-9]{1,6}$"),
)

CASE_TITLE_PATTERNS = (
    re.compile(r"^Test Case test_\d+$"),
    re.compile(r"^Catalog migration case$"),
    re.compile(r"^Block delete$"),
    re.compile(r"^No catalog test_\d+$"),
)

WORK_ITEM_TITLE_PATTERNS = (
    re.compile(r"^Test Requirement test_\d+$"),
    re.compile(r"^Searchable Item test_\d+$"),
    re.compile(r"^Test Transitions test_\d+$"),
    re.compile(r"^Requirement test_\d+$"),
    re.compile(r"^Get Test test_\d+$"),
    re.compile(r"^Original Title test_\d+$"),
    re.compile(r"^Updated Title test_\d+$"),
    re.compile(r"^Delete Test test_\d+$"),
    re.compile(r"^Test Requirement for (Cases|Lifecycle|Reject) test_\d+$"),
)

REQ_TITLE_PATTERNS = (
    re.compile(r"^Test Requirement test_\d+$"),
    re.compile(r"^Req test_\d+$"),
    re.compile(r"^Get Test test_\d+$"),
    re.compile(r"^Original Title test_\d+$"),
    re.compile(r"^Updated Title test_\d+$"),
    re.compile(r"^Delete Test test_\d+$"),
    re.compile(r"^Test desc$"),
)


def is_integration_user(doc: dict[str, Any]) -> bool:
    user_id = str(doc.get("user_id") or "")
    if not user_id or user_id in PRESERVED_USER_IDS:
        return False
    if user_id.startswith(EPHEMERAL_USER_ID_PREFIXES):
        return True
    email = str(doc.get("email") or "")
    return email.endswith("@test.local")


def is_integration_permission(doc: dict[str, Any]) -> bool:
    perm_id = str(doc.get("perm_id") or "")
    if perm_id.startswith(PERM_ID_PREFIXES):
        return True
    return str(doc.get("code") or "").startswith("test.code.test_")


def is_integration_role(doc: dict[str, Any]) -> bool:
    role_id = str(doc.get("role_id") or "")
    if not role_id or role_id in PRESERVED_ROLE_IDS:
        return False
    return role_id.startswith(ROLE_ID_PREFIXES)


def is_integration_nav(doc: dict[str, Any]) -> bool:
    return str(doc.get("view") or "").startswith(NAV_VIEW_PREFIXES)


def is_integration_lab(doc: dict[str, Any]) -> bool:
    code = str(doc.get("code") or "")
    if code.upper() in PRESERVED_LAB_CODES:
        return False
    name = str(doc.get("name") or "")
    if any(p.match(name) for p in LAB_NAME_PATTERNS):
        return True
    if any(p.match(code) for p in LAB_CODE_PATTERNS):
        return True
    lab_id = str(doc.get("lab_id") or "")
    return bool(lab_id.startswith("LAB-L") and re.match(r"^LAB-L\d{8,}$", lab_id))


def is_integration_case(doc: dict[str, Any]) -> bool:
    title = str(doc.get("title") or "")
    if any(p.match(title) for p in CASE_TITLE_PATTERNS):
        return True
    if title.startswith("Req test_"):
        return True
    catalog_path = doc.get("catalog_path") or []
    if catalog_path == ["integration"]:
        return True
    if catalog_path and str(catalog_path[0]).startswith("prefix_"):
        return True
    if catalog_path and str(catalog_path[0]).startswith("seg_"):
        return True
    case_id = str(doc.get("case_id") or "")
    return case_id.startswith("TC-CAT-test_") or case_id.startswith("TC-BLOCK-test_")


def is_junk_catalog_segment(doc: dict[str, Any]) -> bool:
    name = str(doc.get("segment_name") or "")
    if name in JUNK_SEGMENT_NAMES:
        return True
    return name.startswith(JUNK_SEGMENT_PREFIXES)


def is_junk_work_item(doc: dict[str, Any]) -> bool:
    title = str(doc.get("title") or "")
    return any(p.match(title) for p in WORK_ITEM_TITLE_PATTERNS)


def is_junk_requirement(doc: dict[str, Any]) -> bool:
    title = str(doc.get("title") or "")
    if any(p.match(title) for p in REQ_TITLE_PATTERNS):
        return True
    return str(doc.get("description") or "") == "catalog test"


# ---------------------------------------------------------------------------
# Cleanup result
# ---------------------------------------------------------------------------


@dataclass
class CleanupResult:
    module: str
    collection: str
    found: int = 0
    affected: int = 0
    action: str = "delete"  # delete | soft_delete
    samples: list[str] = field(default_factory=list)

    def summary_line(self, *, dry_run: bool = False) -> str:
        if self.found == 0:
            return f"  {self.module:12} {self.collection:22}  0"
        if dry_run:
            verb = "would soft-delete" if self.action == "soft_delete" else "would delete"
            return (
                f"  {self.module:12} {self.collection:22}  "
                f"{self.found:4} found → {verb}"
            )
        verb = "soft-deleted" if self.action == "soft_delete" else "deleted"
        return (
            f"  {self.module:12} {self.collection:22}  "
            f"{self.found:4} found → {self.affected:4} {verb}"
        )


def get_database() -> Database:
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


def _sample_lines(items: list[dict[str, Any]], fmt: Callable[[dict], str], limit: int) -> list[str]:
    lines = [fmt(doc) for doc in items[:limit]]
    if len(items) > limit:
        lines.append(f"  ... and {len(items) - limit} more")
    return lines


def _soft_delete_work_item(db: Database, item_id: str) -> None:
    if ObjectId.is_valid(item_id):
        db["bus_work_items"].update_one(
            {"_id": ObjectId(item_id)},
            {"$set": {"is_deleted": True}},
        )


# ---------------------------------------------------------------------------
# Per-module cleanup
# ---------------------------------------------------------------------------


def cleanup_users(db: Database, *, dry_run: bool, sample_limit: int = 15) -> CleanupResult:
    docs = [d for d in db["users"].find({}, {"user_id": 1, "username": 1, "email": 1}) if is_integration_user(d)]
    ids = [d["user_id"] for d in docs if d.get("user_id")]
    result = CleanupResult("users", "users", found=len(docs), action="delete")
    result.samples = _sample_lines(
        docs,
        lambda d: f"    {d.get('user_id')} | {d.get('username')} | {d.get('email')}",
        sample_limit,
    )
    if not dry_run and ids:
        result.affected = db["users"].delete_many({"user_id": {"$in": ids}}).deleted_count
    return result


def cleanup_permissions(db: Database, *, dry_run: bool, sample_limit: int = 15) -> CleanupResult:
    docs = [
        d for d in db["permissions"].find({}, {"perm_id": 1, "code": 1, "name": 1})
        if is_integration_permission(d)
    ]
    ids = [d["perm_id"] for d in docs if d.get("perm_id")]
    result = CleanupResult("permissions", "permissions", found=len(docs), action="delete")
    result.samples = _sample_lines(
        docs,
        lambda d: f"    {d.get('perm_id')} | {d.get('code')} | {d.get('name')}",
        sample_limit,
    )
    if not dry_run and ids:
        result.affected = db["permissions"].delete_many({"perm_id": {"$in": ids}}).deleted_count
    return result


def cleanup_roles(db: Database, *, dry_run: bool, sample_limit: int = 15) -> CleanupResult:
    docs = [
        d for d in db["roles"].find({}, {"role_id": 1, "name": 1}) if is_integration_role(d)
    ]
    ids = [d["role_id"] for d in docs if d.get("role_id")]
    result = CleanupResult("roles", "roles", found=len(docs), action="delete")
    result.samples = _sample_lines(
        docs,
        lambda d: f"    {d.get('role_id')} | {d.get('name')}",
        sample_limit,
    )
    if not dry_run and ids:
        result.affected = db["roles"].delete_many({"role_id": {"$in": ids}}).deleted_count
    return result


def cleanup_navigation(db: Database, *, dry_run: bool, sample_limit: int = 15) -> CleanupResult:
    docs = [
        d for d in db["navigation_pages"].find({}, {"view": 1, "title": 1})
        if is_integration_nav(d)
    ]
    views = [d["view"] for d in docs if d.get("view")]
    result = CleanupResult("navigation", "navigation_pages", found=len(docs), action="delete")
    result.samples = _sample_lines(
        docs,
        lambda d: f"    {d.get('view')} | {d.get('title')}",
        sample_limit,
    )
    if not dry_run and views:
        result.affected = db["navigation_pages"].delete_many({"view": {"$in": views}}).deleted_count
    return result


def cleanup_catalog(db: Database, *, dry_run: bool, sample_limit: int = 15) -> list[CleanupResult]:
    """Catalog labs, test cases, and orphan integration segments."""
    results: list[CleanupResult] = []

    junk_labs = [d for d in db["test_labs"].find({}) if is_integration_lab(d)]
    junk_lab_ids = [d["lab_id"] for d in junk_labs if d.get("lab_id")]

    case_query: list[dict[str, Any]] = [
        {"title": {"$regex": r"^Test Case test_\d+$"}},
        {"title": {"$in": ["Catalog migration case", "Block delete"]}},
        {"catalog_path": ["integration"]},
        {"case_id": {"$regex": r"^TC-(CAT|BLOCK)-test_"}},
    ]
    if junk_lab_ids:
        case_query.append({"lab_id": {"$in": junk_lab_ids}})

    junk_cases = [
        d for d in db["test_cases"].find(
            {"$or": case_query},
            {"case_id": 1, "title": 1, "lab_id": 1, "workflow_item_id": 1, "catalog_path": 1},
        )
        if is_integration_case(d)
    ]
    case_ids = [d["case_id"] for d in junk_cases if d.get("case_id")]

    junk_segments = [
        d for d in db["test_catalog_segments"].find({})
        if is_junk_catalog_segment(d)
    ]
    segment_ids = [d["_id"] for d in junk_segments]

    lab_result = CleanupResult("catalog", "test_labs", found=len(junk_labs), action="delete")
    lab_result.samples = _sample_lines(
        junk_labs,
        lambda d: f"    {d.get('lab_id')} | {d.get('code')} | {d.get('name')}",
        sample_limit,
    )
    case_result = CleanupResult("catalog", "test_cases", found=len(junk_cases), action="soft_delete")
    case_result.samples = _sample_lines(
        junk_cases,
        lambda d: f"    {d.get('case_id')} | {d.get('title')} | {d.get('lab_id')}",
        sample_limit,
    )
    seg_result = CleanupResult("catalog", "test_catalog_segments", found=len(junk_segments), action="delete")
    seg_result.samples = _sample_lines(
        junk_segments,
        lambda d: f"    {d.get('lab_id')} | {d.get('segment_name')} | parent={d.get('parent_path')}",
        sample_limit,
    )

    if not dry_run:
        if case_ids:
            db["test_cases"].update_many(
                {"case_id": {"$in": case_ids}},
                {"$set": {"is_deleted": True}},
            )
            case_result.affected = len(case_ids)
            for doc in junk_cases:
                wf_id = doc.get("workflow_item_id")
                if wf_id:
                    _soft_delete_work_item(db, str(wf_id))
        if junk_lab_ids:
            db["test_catalog_segments"].delete_many({"lab_id": {"$in": junk_lab_ids}})
            lab_result.affected = db["test_labs"].delete_many(
                {"lab_id": {"$in": junk_lab_ids}}
            ).deleted_count
        if segment_ids:
            seg_result.affected = db["test_catalog_segments"].delete_many(
                {"_id": {"$in": segment_ids}}
            ).deleted_count

    results.extend([lab_result, case_result, seg_result])
    return results


def cleanup_workflow(db: Database, *, dry_run: bool, sample_limit: int = 15) -> list[CleanupResult]:
    junk_items = [
        d for d in db["bus_work_items"].find({"is_deleted": False}, {"title": 1})
        if is_junk_work_item(d)
    ]
    item_ids = [d["_id"] for d in junk_items]

    junk_reqs = [
        d for d in db["test_requirements"].find(
            {"is_deleted": False},
            {"req_id": 1, "title": 1, "workflow_item_id": 1},
        )
        if is_junk_requirement(d)
    ]
    req_ids = [d["req_id"] for d in junk_reqs if d.get("req_id")]

    wi_result = CleanupResult("workflow", "bus_work_items", found=len(junk_items), action="soft_delete")
    wi_result.samples = _sample_lines(
        junk_items,
        lambda d: f"    {d['_id']} | {d.get('title')}",
        sample_limit,
    )
    req_result = CleanupResult("workflow", "test_requirements", found=len(junk_reqs), action="soft_delete")
    req_result.samples = _sample_lines(
        junk_reqs,
        lambda d: f"    {d.get('req_id')} | {d.get('title')}",
        sample_limit,
    )

    if not dry_run:
        if item_ids:
            db["bus_work_items"].update_many(
                {"_id": {"$in": item_ids}},
                {"$set": {"is_deleted": True}},
            )
            wi_result.affected = len(item_ids)
        if req_ids:
            db["test_requirements"].update_many(
                {"req_id": {"$in": req_ids}},
                {"$set": {"is_deleted": True}},
            )
            req_result.affected = len(req_ids)
            for doc in junk_reqs:
                wf_id = doc.get("workflow_item_id")
                if wf_id:
                    _soft_delete_work_item(db, str(wf_id))

    return [wi_result, req_result]


MODULE_RUNNERS: dict[str, Callable[..., list[CleanupResult] | CleanupResult]] = {
    "users": cleanup_users,
    "permissions": cleanup_permissions,
    "roles": cleanup_roles,
    "navigation": cleanup_navigation,
    "catalog": cleanup_catalog,
    "workflow": cleanup_workflow,
}


def run_cleanup(
    modules: list[str] | None = None,
    *,
    dry_run: bool = False,
    verbose: bool = False,
    sample_limit: int = 15,
) -> list[CleanupResult]:
    """Run cleanup for selected modules; returns all result rows."""
    selected = modules or list(ALL_MODULES)
    unknown = set(selected) - set(ALL_MODULES)
    if unknown:
        raise ValueError(f"Unknown module(s): {', '.join(sorted(unknown))}")

    db = get_database()
    all_results: list[CleanupResult] = []

    for name in ALL_MODULES:
        if name not in selected:
            continue
        runner = MODULE_RUNNERS[name]
        out = runner(db, dry_run=dry_run, sample_limit=sample_limit)
        if isinstance(out, list):
            all_results.extend(out)
        else:
            all_results.append(out)

    if verbose:
        for r in all_results:
            print(f"\n[{r.module}/{r.collection}]")
            for line in r.samples:
                print(line)

    return all_results
