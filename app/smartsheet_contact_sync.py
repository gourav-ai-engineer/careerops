from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import Contact, Job
from app.smartsheet_sync import SmartsheetClient


@dataclass(frozen=True)
class ContactColumnMap:
    recruiter_contact: int
    recruiter_linkedin: int
    recruiter_verification: int


JOB_CONTACT_COLUMNS = ContactColumnMap(
    recruiter_contact=6946891809722244,
    recruiter_linkedin=1317392275509124,
    recruiter_verification=1865803764633476,
)


@dataclass(frozen=True)
class ContactSyncOperation:
    action: str
    job_id: int
    row_id: int | None
    reason: str
    cells: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ContactSyncPlan:
    sheet_id: int
    operations: tuple[ContactSyncOperation, ...]


ELIGIBLE_CONTACT_STATUSES = frozenset({"source_checked", "verified"})


def _cell_value(cell: dict[str, Any]) -> Any:
    return cell.get("displayValue", cell.get("value"))


def _job_key(job: Job) -> tuple[str, str, str]:
    return (
        job.company.name.strip().casefold(),
        job.title.strip().casefold(),
        (job.application_url or "").strip(),
    )


def _row_values(row: dict[str, Any]) -> dict[int, Any]:
    return {cell["columnId"]: _cell_value(cell) for cell in row.get("cells", [])}


def _row_key(values: dict[int, Any]) -> tuple[str, str, str]:
    return (
        str(values.get(5398779437813636) or "").strip().casefold(),
        str(values.get(3146979624128388) or "").strip().casefold(),
        str(values.get(191492368666500) or "").strip(),
    )


def _index_rows(
    sheet: dict[str, Any],
) -> tuple[
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str], list[dict[str, Any]]],
]:
    exact: dict[tuple[str, str, str], dict[str, Any]] = {}
    fallback: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in sheet.get("rows", []):
        values = _row_values(row)
        key = _row_key(values)
        if key[0] and key[1]:
            exact[key] = row
            fallback.setdefault((key[0], key[1]), []).append(row)
    return exact, fallback


def _contact_summary(contacts: list[Contact]) -> tuple[str, str, str]:
    eligible = [
        contact
        for contact in contacts
        if contact.verification_status in ELIGIBLE_CONTACT_STATUSES
    ]
    eligible.sort(
        key=lambda contact: (
            0 if contact.verification_status == "verified" else 1,
            (contact.priority or "").casefold(),
            (contact.name or "").casefold(),
            contact.id,
        )
    )

    descriptions: list[str] = []
    linkedin: list[str] = []
    verification: list[str] = []

    for contact in eligible[:5]:
        label = contact.name or contact.title or "Public contact"
        if contact.title and contact.name:
            label = f"{contact.name} — {contact.title}"
        if contact.email:
            label += f" <{contact.email}>"
        if contact.phone and contact.phone_type:
            label += f" | {contact.phone_type}: {contact.phone}"
        descriptions.append(label)
        if contact.linkedin_url:
            linkedin.append(contact.linkedin_url)
        verification.append(
            f"{label}: {contact.verification_status}"
            + (f" ({contact.verification_confidence})" if contact.verification_confidence else "")
        )

    return (
        " | ".join(descriptions),
        " | ".join(dict.fromkeys(linkedin)),
        " | ".join(verification),
    )


def build_contact_sync_plan(
    jobs: list[Job],
    sheet: dict[str, Any],
) -> ContactSyncPlan:
    exact, fallback = _index_rows(sheet)
    operations: list[ContactSyncOperation] = []

    for job in jobs:
        contacts = [link.contact for link in job.contacts if link.contact is not None]
        contact_text, linkedin_text, verification_text = _contact_summary(contacts)

        if not contact_text:
            operations.append(
                ContactSyncOperation(
                    action="skip",
                    job_id=job.id,
                    row_id=None,
                    reason="No linked contact has source_checked or verified status",
                )
            )
            continue

        key = _job_key(job)
        row = exact.get(key)
        if row is None:
            matches = fallback.get((key[0], key[1]), [])
            if len(matches) == 1:
                row = matches[0]

        if row is None:
            operations.append(
                ContactSyncOperation(
                    action="skip",
                    job_id=job.id,
                    row_id=None,
                    reason="No existing job row; sync the job before syncing contacts",
                )
            )
            continue

        desired: list[dict[str, Any]] = [
            {"columnId": JOB_CONTACT_COLUMNS.recruiter_contact, "value": contact_text},
            {"columnId": JOB_CONTACT_COLUMNS.recruiter_verification, "value": verification_text},
        ]
        if linkedin_text:
            desired.insert(
                1,
                {"columnId": JOB_CONTACT_COLUMNS.recruiter_linkedin, "value": linkedin_text},
            )

        existing = _row_values(row)
        changed = any(
            existing.get(cell["columnId"]) != cell["value"] for cell in desired
        )

        if changed:
            operations.append(
                ContactSyncOperation(
                    action="update",
                    job_id=job.id,
                    row_id=row["id"],
                    reason="Public contact fields differ from PostgreSQL contact records",
                    cells=tuple(desired),
                )
            )

    return ContactSyncPlan(sheet_id=sheet["id"], operations=tuple(operations))


def apply_contact_sync_plan(
    client: SmartsheetClient,
    plan: ContactSyncPlan,
) -> dict[str, int]:
    updates = [
        {"id": op.row_id, "cells": list(op.cells)}
        for op in plan.operations
        if op.action == "update" and op.row_id is not None
    ]
    if updates:
        client.update_rows(plan.sheet_id, updates)

    unchanged = sum(op.action == "unchanged" for op in plan.operations)
    return {
        "updated": len(updates),
        "skipped": sum(op.action == "skip" for op in plan.operations),
        "unchanged": unchanged,
    }
