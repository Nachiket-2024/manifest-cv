from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..resume_document_table.resume_document_model import ResumeDocument


class ResumeDocumentRepository:
    """
    Persistence layer for finalized resume PDFs. Scoped to callers already
    holding a resume_draft_id they've verified belongs to the requesting
    user (see api/document_routes/document_routes.py) — this repository
    itself has no user_id column to filter by, since ownership flows
    through the parent resume_drafts row.
    """

    @staticmethod
    async def get_by_draft_id(resume_draft_id: int, db: AsyncSession) -> ResumeDocument | None:
        stmt = select(ResumeDocument).where(ResumeDocument.resume_draft_id == resume_draft_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert(
        resume_draft_id: int, template_id: str, tex_source: str, pdf_bytes: bytes, db: AsyncSession
    ) -> ResumeDocument:
        # Atomic INSERT ... ON CONFLICT DO UPDATE rather than a check-then-act
        # SELECT+INSERT/UPDATE — resume_draft_id is unique, so two concurrent
        # finalize calls for the same draft would otherwise both see "no
        # existing row" and race an unhandled IntegrityError on the second
        # INSERT instead of both landing cleanly.
        stmt = insert(ResumeDocument).values(
            resume_draft_id=resume_draft_id,
            template_id=template_id,
            tex_source=tex_source,
            pdf_bytes=pdf_bytes,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ResumeDocument.resume_draft_id],
            set_={
                "template_id": stmt.excluded.template_id,
                "tex_source": stmt.excluded.tex_source,
                "pdf_bytes": stmt.excluded.pdf_bytes,
                # onupdate=func.now() on the column is an ORM unit-of-work
                # feature and never fires for this Core-level statement, so
                # it must be set explicitly here to still bump on conflict.
                "updated_at": func.now(),
            },
        ).returning(ResumeDocument)

        result = await db.execute(stmt)
        await db.commit()
        entry = result.scalar_one()
        await db.refresh(entry)
        return entry


resume_document_repository = ResumeDocumentRepository()
