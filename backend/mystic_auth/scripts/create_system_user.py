import asyncio
import getpass

from ..auth.password_logic.password_service import password_service
from ..authorization.policies.default_policies import (
    SELF_SERVICE_POLICY_NAME,
    SYSTEM_SUPERUSER_POLICY_NAME,
    USER_ADMINISTRATION_POLICY_NAME,
)

# PBAC: the system superuser's actual access comes from holding every
# baseline policy, assigned explicitly here — not from role="system".
from ..authorization.repositories.policy_repository import policy_repository
from ..database.connection import database
from ..logging.logging_config import get_logger
from ..user_crud.user_crud_collector import user_crud

# UserRole is kept as display/grouping metadata for the system account; it no
# longer grants any access itself (see PBAC policy assignment below).
from ..user_table.user_model import UserRole

logger = get_logger(__name__)

SYSTEM_ROLE = UserRole.system

# Every baseline policy the system superuser must hold, so it has strictly
# greater access than any other account (self-service + user administration +
# the system-only actions).
SYSTEM_USER_POLICY_NAMES = (
    SELF_SERVICE_POLICY_NAME,
    USER_ADMINISTRATION_POLICY_NAME,
    SYSTEM_SUPERUSER_POLICY_NAME,
)


async def create_system_user():
    """
    Interactive CLI script to create the one-time system superuser.

    Run once manually before first launch:
        python -m mystic_auth.scripts.create_system_user
    """
    print("\n--- System Superuser Creation ---")

    name     = input("Enter system user name: ").strip()
    email    = input("Enter system user email: ").strip()
    password = getpass.getpass("Enter system user password: ")

    async for db in database.get_session():

        existing = await user_crud.get_by_email(email, db)
        if existing:
            print(f"\n A user with email '{email}' already exists.")
            logger.warning("System user creation failed — email already exists: %s", email)
            return

        hashed_password = await password_service.hash_password(password)

        new_user = await user_crud.create({
            "name":            name,
            "email":           email,
            "hashed_password": hashed_password,
            "role":            SYSTEM_ROLE,   # Display/grouping metadata only
            "is_verified":     True,          # No email verification needed for system user
            "is_active":       True,          # Fully active from the moment of creation
        }, db)

        # Assign every baseline policy — the actual source of this account's
        # system-superuser access, per PBAC.
        for policy_name in SYSTEM_USER_POLICY_NAMES:
            policy = await policy_repository.get_by_name(policy_name, db)
            if not policy:
                logger.error(
                    "Baseline policy '%s' not found — run migrations before creating the system user",
                    policy_name,
                )
                print(f"\n Baseline policy '{policy_name}' not found. Run migrations first.")
                return
            await policy_repository.assign_policy_to_user(
                user_id=new_user.id, policy_id=policy.id, db=db, assigned_by="system"
            )

        print(f"\n System user '{email}' created successfully.")
        logger.info("System user created successfully: %s", email)


if __name__ == "__main__":
    asyncio.run(create_system_user())
