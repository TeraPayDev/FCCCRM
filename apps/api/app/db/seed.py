from __future__ import annotations

from sqlalchemy import select

from app.db.session import get_session_factory
from app.models.identity import Organisation, Role

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


if __name__ == "__main__":
    seed()
    print("CRAM Milestone 4 seed data applied successfully.")
