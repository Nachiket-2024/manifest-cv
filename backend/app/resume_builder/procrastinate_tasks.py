"""ManifestCV resume tasks registered on Mystic Auth's Procrastinate app."""
from ..sdk import procrastinate_app


@procrastinate_app.task(name="app.resume_builder.generate_resume_job")
async def generate_resume_job(job_id: int) -> None:
    # Import lazily to keep task registration independent from route imports.
    from ..api.resume_builder_routes.job_routes import _run_generation_job

    await _run_generation_job(job_id)


@procrastinate_app.task(name="app.resume_builder.render_resume_job")
async def render_resume_job(job_id: int) -> None:
    from ..api.resume_builder_routes.job_routes import _run_render_job

    await _run_render_job(job_id)
