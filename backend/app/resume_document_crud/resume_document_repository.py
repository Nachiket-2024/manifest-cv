from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        existing = await ResumeDocumentRepository.get_by_draft_id(resume_draft_id, db)
        if existing is not None:
            existing.template_id = template_id
            existing.tex_source = tex_source
            existing.pdf_bytes = pdf_bytes
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing

        entry = ResumeDocument(
            resume_draft_id=resume_draft_id,
            template_id=template_id,
            tex_source=tex_source,
            pdf_bytes=pdf_bytes,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry


resume_document_repository = ResumeDocumentRepository()
