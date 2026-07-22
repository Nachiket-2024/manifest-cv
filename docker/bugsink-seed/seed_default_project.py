# Piped into `bugsink-manage shell` by the `seed_bugsink_project` service
# (docker-compose.yml) — Bugsink ships with no seed data, so a first login
# would otherwise have no Team/Project to click into. Idempotent: no-op if
# a project already exists.
import os

from django.contrib.auth import get_user_model

from teams.models import Team, TeamMembership, TeamRole
from projects.models import Project, ProjectMembership, ProjectRole, ProjectVisibility

User = get_user_model()

if Project.objects.filter(is_deleted=False).exists():
    print("seed_bugsink_project: a project already exists, nothing to seed.")
else:
    # Matches this app's own APP_NAME (see .env.example) so the default
    # project reads as "this app's errors", not a generic placeholder —
    # falls back to "ManifestCV" if APP_NAME was somehow left unset.
    name = os.environ.get("APP_NAME", "ManifestCV")

    team, _ = Team.objects.get_or_create(name=name)
    project, _ = Project.objects.get_or_create(
        name=name,
        defaults={
            "team": team,
            "slug": name.lower().replace(" ", "-"),
            "visibility": ProjectVisibility.TEAM_MEMBERS,
        },
    )

    # Membership, not just existence, is what actually makes the project
    # show up under "My projects" for the one user this template creates
    # automatically (CREATE_SUPERUSER, see docker-compose.yml) — without
    # it, a non-superuser Bugsink login would still see an empty list even
    # though the project technically exists.
    superuser = User.objects.filter(is_superuser=True).order_by("id").first()
    if superuser is not None:
        TeamMembership.objects.get_or_create(
            team=team, user=superuser, defaults={"role": TeamRole.ADMIN, "accepted": True}
        )
        ProjectMembership.objects.get_or_create(
            project=project, user=superuser, defaults={"role": ProjectRole.ADMIN, "accepted": True}
        )

    print(f"seed_bugsink_project: created project '{project.name}' (team '{team.name}').")
    print(f"seed_bugsink_project: DSN = {project.dsn}")
    print("seed_bugsink_project: put the appropriate host form of this DSN into SENTRY_DSN / VITE_SENTRY_DSN — see docs/error-monitoring/overview.md.")
