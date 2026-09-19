from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.models import Job
from app.settings import settings


@dataclass(frozen=True)
class SmartsheetColumnMap:
    company: int
    role: int
    location: int
    eligibility: int
    fit_score: int
    application_status: int
    apply_link: int
    source: int
    last_checked: int


JOB_SHEET_COLUMNS = SmartsheetColumnMap(
    company=5398779437813636,
    role=3146979624128388,
    location=7650579251498884,
    eligibility=2021079717285764,
    fit_score=6524679344656260,
    application_status=8776479158341508,
    apply_link=191492368666500,
    source=4695091996036996,
    last_checked=2443292182351748,
)


@dataclass(frozen=True)
class SyncOperation:
    action: str
    job_id: int
    reason: str
    row_id: int | None = None
    cells: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class SyncPlan:
    sheet_id: int
    operations: tuple[SyncOperation, ...]


class SmartsheetClient:
    BASE_URL = "https://api.smartsheet.com/2.0"

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or settings.smartsheet_access_token
        if not self.access_token:
            raise ValueError("SMARTSHEET_ACCESS_TOKEN is not configured")

    def _request(self, method: str, path: str, *, payload: Any | None = None) -> dict[str, Any]:
        response = httpx.request(
            method,
            f"{self.BASE_URL}{path}",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    def get_sheet(self, sheet_id: int) -> dict[str, Any]:
        return self._request("GET", f"/sheets/{sheet_id}")

    def add_rows(self, sheet_id: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request("POST", f"/sheets/{sheet_id}/rows", payload=rows)

    def update_rows(self, sheet_id: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request("PUT", f"/sheets/{sheet_id}/rows", payload=rows)


def _cell_value(cell: dict[str, Any]) -> Any:
    return cell.get("displayValue", cell.get("value"))


def _row_key(values: dict[int, Any]) -> tuple[str, str, str]:
    return (
        str(values.get(JOB_SHEET_COLUMNS.company) or "").strip().casefold(),
        str(values.get(JOB_SHEET_COLUMNS.role) or "").strip().casefold(),
        str(values.get(JOB_SHEET_COLUMNS.apply_link) or "").strip(),
    )


def _index_existing_rows(sheet: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in sheet.get("rows", []):
        values = {cell["columnId"]: _cell_value(cell) for cell in row.get("cells", [])}
        key = _row_key(values)
        if key[0] and key[1]:
            index[key] = row
    return index


def _key(job: Job) -> tuple[str, str, str]:
    return (
        job.company.name.strip().casefold(),
        job.title.strip().casefold(),
        (job.application_url or "").strip(),
    )


def _cells(job: Job, fit_score: int | None = None) -> tuple[dict[str, Any], ...]:
    values = {
        JOB_SHEET_COLUMNS.company: job.company.name,
        JOB_SHEET_COLUMNS.role: job.title,
        JOB_SHEET_COLUMNS.location: job.location,
        JOB_SHEET_COLUMNS.eligibility: job.eligibility,
        JOB_SHEET_COLUMNS.fit_score: fit_score,
        JOB_SHEET_COLUMNS.application_status: job.status,
        JOB_SHEET_COLUMNS.apply_link: job.application_url,
        JOB_SHEET_COLUMNS.source: job.source_url,
        JOB_SHEET_COLUMNS.last_checked: job.last_checked_at.isoformat() if job.last_checked_at else None,
    }
    return tuple(
        {"columnId": column_id, "value": value}
        for column_id, value in values.items()
        if value not in (None, "")
    )


def build_job_sync_plan(
    jobs: list[Job],
    sheet: dict[str, Any],
    fit_scores: dict[int, int] | None = None,
) -> SyncPlan:
    exact_index = _index_existing_rows(sheet)
    fallback: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in sheet.get("rows", []):
        values = {cell["columnId"]: _cell_value(cell) for cell in row.get("cells", [])}
        key = _row_key(values)
        if key[0] and key[1]:
            fallback.setdefault((key[0], key[1]), []).append(row)

    fit_scores = fit_scores or {}
    operations: list[SyncOperation] = []

    for job in jobs:
        cells = _cells(job, fit_scores.get(job.id))
        row = exact_index.get(_key(job))

        # When one side has no apply URL, allow a fallback company+role match
        # only if it is unique. This avoids obvious duplicates without merging
        # multiple roles that happen to share a company/title pair.
        if row is None:
            matches = fallback.get((_key(job)[0], _key(job)[1]), [])
            if len(matches) == 1:
                row = matches[0]

        if row is None:
            operations.append(
                SyncOperation(
                    action="add",
                    job_id=job.id,
                    reason="No matching company/title/application-link row exists",
                    cells=cells,
                )
            )
            continue

        existing_values = {
            cell["columnId"]: _cell_value(cell)
            for cell in row.get("cells", [])
        }
        desired = {cell["columnId"]: cell["value"] for cell in cells}
        if any(existing_values.get(column_id) != value for column_id, value in desired.items()):
            operations.append(
                SyncOperation(
                    action="update",
                    job_id=job.id,
                    row_id=row["id"],
                    reason="Tracked PostgreSQL fields differ from Smartsheet",
                    cells=cells,
                )
            )

    return SyncPlan(sheet_id=sheet["id"], operations=tuple(operations))


def apply_job_sync_plan(client: SmartsheetClient, plan: SyncPlan) -> dict[str, int]:
    adds = [
        {"toBottom": True, "cells": list(operation.cells)}
        for operation in plan.operations
        if operation.action == "add"
    ]
    updates = [
        {"id": operation.row_id, "cells": list(operation.cells)}
        for operation in plan.operations
        if operation.action == "update" and operation.row_id is not None
    ]

    added = updated = 0
    if adds:
        client.add_rows(plan.sheet_id, adds)
        added = len(adds)
    if updates:
        client.update_rows(plan.sheet_id, updates)
        updated = len(updates)
    return {"added": added, "updated": updated, "unchanged": 0}
