from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Job, ResumeDocument, ResumeDraft


@dataclass(frozen=True)
class TailoringResult:
    content: str
    change_plan: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}", text.lower())}


def tailor_resume(master: str, job_text: str, required_skills: list[str]) -> TailoringResult:
    resume_tokens = _tokens(master)
    requirements = list(dict.fromkeys(skill.strip() for skill in required_skills if skill.strip()))
    matched = [skill for skill in requirements if skill.lower() in resume_tokens or skill.lower() in master.lower()]
    missing = [skill for skill in requirements if skill not in matched]
    plan = [
        "Keep factual experience, education, projects, and metrics unchanged.",
        "Prioritize matched required skills in the skills section when they are already supported by the master resume.",
    ]
    if missing:
        plan.append("Do not invent missing skills. Add them only after acquiring real evidence or project experience.")
    else:
        plan.append("All extracted required skills are already represented in the master resume.")
    return TailoringResult(content=master, change_plan=plan, matched_keywords=matched, missing_keywords=missing)


def save_master_resume(db: Session, *, name: str, content: str) -> ResumeDocument:
    existing = db.scalar(select(ResumeDocument).where(ResumeDocument.is_master.is_(True)))
    if existing is None:
        existing = ResumeDocument(name=name.strip(), document_type="master", version=1, content=content, is_master=True)
        db.add(existing)
    else:
        existing.version += 1
        existing.name = name.strip()
        existing.content = content
    db.commit()
    db.refresh(existing)
    return existing


def get_master_resume(db: Session) -> ResumeDocument | None:
    return db.scalar(select(ResumeDocument).where(ResumeDocument.is_master.is_(True)))


def create_resume_draft(db: Session, job_id: int) -> ResumeDraft:
    job = db.scalar(select(Job).options(selectinload(Job.requirements)).where(Job.id == job_id))
    if job is None:
        raise ValueError("Job not found")
    master = get_master_resume(db)
    if master is None:
        raise ValueError("Master resume not found")
    skills = json.loads(job.requirements.required_skills) if job.requirements and job.requirements.required_skills else []
    job_text = " ".join(filter(None, [job.title, job.role_family, job.eligibility, json.dumps(skills)]))
    result = tailor_resume(master.content, job_text, skills)
    existing = db.scalar(
        select(ResumeDraft)
        .where(ResumeDraft.job_id == job_id, ResumeDraft.status == "draft")
        .order_by(ResumeDraft.created_at.desc())
    )
    if existing is not None:
        existing.master_resume_id = master.id
        existing.content = result.content
        existing.change_plan = json.dumps(result.change_plan)
        existing.matched_keywords = json.dumps(result.matched_keywords)
        existing.missing_keywords = json.dumps(result.missing_keywords)
        db.commit()
        db.refresh(existing)
        return existing
    draft = ResumeDraft(
        job_id=job.id, master_resume_id=master.id, content=result.content,
        change_plan=json.dumps(result.change_plan),
        matched_keywords=json.dumps(result.matched_keywords),
        missing_keywords=json.dumps(result.missing_keywords),
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft
