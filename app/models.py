from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("company_id", "title", "application_url", name="uq_job_identity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    role_family: Mapped[str | None] = mapped_column(String(100))
    application_url: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    eligibility: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(50), default="discovered", nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    company: Mapped[Company] = relationship(back_populates="jobs")
    contacts: Mapped[list["JobContact"]] = relationship(back_populates="job")
    source_evidence: Mapped[list["JobSourceEvidence"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["JobStatusHistory"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobStatusHistory.changed_at.desc()",
    )


class JobSourceEvidence(Base):
    __tablename__ = "job_source_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="source")
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="needs_review")
    verification_reason: Mapped[str] = mapped_column(Text, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[Job] = relationship(back_populates="source_evidence")


class JobStatusHistory(Base):
    __tablename__ = "job_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[Job] = relationship(back_populates="status_history")


class CandidateProfileRecord(Base):
    __tablename__ = "candidate_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role_families: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    preferred_locations: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    skills: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    experience_keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    work_authorization: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    normalized_email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    phone_type: Mapped[str | None] = mapped_column(String(50))
    contact_type: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str | None] = mapped_column(String(50))
    verification_confidence: Mapped[str | None] = mapped_column(String(20))
    verification_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str | None] = mapped_column(String(10))
    company: Mapped[Company] = relationship(back_populates="contacts")
    jobs: Mapped[list["JobContact"]] = relationship(back_populates="jobs")


class JobContact(Base):
    __tablename__ = "job_contacts"
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), primary_key=True)
    relevance_reason: Mapped[str | None] = mapped_column(Text)
    job: Mapped[Job] = relationship(back_populates="contacts")
    contact: Mapped[Contact] = relationship(back_populates="jobs")
