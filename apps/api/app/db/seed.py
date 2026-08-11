from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_session_factory
from app.models.identity import Organisation, Permission, Role, User
from app.security.passwords import hash_password

ORGANISATIONS = (
    ("FCC", "Freetown City Council"),
    ("NaCSA", "NaCSA"),
    ("NDMA", "NDMA"),
    ("SL-Met", "SL-Met"),
    ("Stats-SL", "Statistics Sierra Leone"),
    ("ONS", "ONS"),
)

SYSTEM_ROLES = (
    ("system_administrator", "System Administrator"),
    ("fcc_administrator", "FCC Administrator"),
    ("data_steward", "Data Steward"),
    ("climate_analyst", "Climate Analyst"),
    ("agency_analyst", "Agency Analyst"),
    ("executive_user", "Executive User"),
    ("public_user", "Public User"),
)

PERMISSIONS = (
    ("users.read", "View users and identity metadata"),
    ("users.manage", "Manage users, role assignments, and account state"),
    ("datasets.read", "View dataset catalogue and version metadata"),
    ("datasets.manage", "Manage dataset metadata and lifecycle operations"),
    ("datasets.upload", "Upload source files and create dataset versions"),
    ("datasets.validate", "Run dataset validation rules"),
    ("datasets.approve", "Approve or reject validated dataset versions"),
    ("datasets.publish", "Publish approved dataset versions"),
    ("gis.read", "View GIS layer metadata"),
    ("gis.manage", "Manage GIS layer metadata"),
    ("analytics.read", "View analytics outputs"),
    ("analytics.manage", "Manage analytics configuration where authorized"),
    ("citizen_reports.read", "View permitted citizen reports"),
    ("citizen_reports.manage", "Manage permitted citizen-report workflows"),
    ("reports.read", "View generated reports"),
    ("reports.manage", "Generate/manage reports"),
    ("audit.read", "View audit records"),
)

ROLE_PERMISSION_MATRIX = {
    "system_administrator": {code for code, _ in PERMISSIONS},
    "fcc_administrator": {code for code, _ in PERMISSIONS},
    "data_steward": {
        "datasets.read",
        "datasets.manage",
        "datasets.upload",
        "datasets.validate",
        "gis.read",
        "gis.manage",
        "analytics.read",
        "reports.read",
        "audit.read",
    },
    "climate_analyst": {
        "datasets.read",
        "gis.read",
        "analytics.read",
        "analytics.manage",
        "reports.read",
        "reports.manage",
    },
    "agency_analyst": {
        "datasets.read",
        "gis.read",
        "analytics.read",
        "reports.read",
    },
    "executive_user": {
        "datasets.read",
        "gis.read",
        "analytics.read",
        "reports.read",
    },
    "public_user": set(),
}


def seed() -> None:
    factory = get_session_factory()
    with factory() as session, session.begin():
        existing_orgs = set(session.scalars(select(Organisation.code)).all())
        for code, name in ORGANISATIONS:
            if code not in existing_orgs:
                session.add(Organisation(code=code, name=name))

        existing_roles = set(session.scalars(select(Role.code)).all())
        for code, name in SYSTEM_ROLES:
            if code not in existing_roles:
                session.add(Role(code=code, name=name))

        existing_permissions = set(session.scalars(select(Permission.code)).all())
        for code, description in PERMISSIONS:
            if code not in existing_permissions:
                session.add(Permission(code=code, description=description))

    with factory() as session, session.begin():
        roles = {
            role.code: role
            for role in session.scalars(select(Role).options(selectinload(Role.permissions))).all()
        }
        permissions = {
            permission.code: permission for permission in session.scalars(select(Permission)).all()
        }
        for role_code, permission_codes in ROLE_PERMISSION_MATRIX.items():
            role = roles[role_code]
            role.permissions = [permissions[code] for code in sorted(permission_codes)]


def seed_development_admin() -> None:
    password = os.getenv("CRAM_BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError(
            "CRAM_BOOTSTRAP_ADMIN_PASSWORD is required for development admin bootstrap."
        )

    factory = get_session_factory()
    with factory() as session, session.begin():
        fcc = session.scalar(select(Organisation).where(Organisation.code == "FCC"))
        admin_role = session.scalar(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.code == "system_administrator")
        )
        if fcc is None or admin_role is None:
            raise RuntimeError("Run the standard seed before development admin bootstrap.")

        user = session.scalar(select(User).where(User.username == "cramadmin"))
        if user is None:
            user = User(
                username="cramadmin",
                email="cramadmin@development.local",
                organisation_id=fcc.id,
                password_hash=hash_password(password),
                is_active=True,
            )
            user.roles = [admin_role]
            session.add(user)
        else:
            user.password_hash = hash_password(password)
            user.is_active = True
            user.failed_login_attempts = 0
            user.locked_until = None
            user.roles = [admin_role]


if __name__ == "__main__":
    seed()
    print("CRAM Milestone 5 RBAC seed matrix applied successfully.")
