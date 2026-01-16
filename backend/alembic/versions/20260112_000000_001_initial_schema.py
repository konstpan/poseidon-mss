"""Initial database schema for Poseidon MSS

Revision ID: 001
Revises:
Create Date: 2026-01-12 00:00:00.000000

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS ais")
    op.execute("CREATE SCHEMA IF NOT EXISTS security")

    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create vessels table
    op.create_table(
        "vessels",
        sa.Column("mmsi", sa.String(length=9), nullable=False),
        sa.Column("imo", sa.String(length=10), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("call_sign", sa.String(length=50), nullable=True),
        sa.Column("ship_type", sa.Integer(), nullable=True),
        sa.Column("ship_type_text", sa.String(length=100), nullable=True),
        sa.Column("dimension_a", sa.Integer(), nullable=True),
        sa.Column("dimension_b", sa.Integer(), nullable=True),
        sa.Column("dimension_c", sa.Integer(), nullable=True),
        sa.Column("dimension_d", sa.Integer(), nullable=True),
        sa.Column("length", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("draught", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("eta", sa.DateTime(), nullable=True),
        sa.Column("flag_state", sa.String(length=2), nullable=True),
        sa.Column("risk_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("risk_category", sa.String(length=20), nullable=True),
        sa.Column("last_latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("last_longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("last_speed", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("last_course", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("last_position_time", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("mmsi", name=op.f("pk_vessels")),
        schema="ais",
    )
    op.create_index("ix_vessels_name", "vessels", ["name"], schema="ais")
    op.create_index("ix_vessels_ship_type", "vessels", ["ship_type"], schema="ais")
    op.create_index("ix_vessels_flag_state", "vessels", ["flag_state"], schema="ais")
    op.create_index("ix_vessels_risk_score", "vessels", ["risk_score"], schema="ais")

    # Create vessel_positions table
    op.create_table(
        "vessel_positions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mmsi", sa.String(length=9), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column(
            "position",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=False,
        ),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("speed", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("course", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("heading", sa.Integer(), nullable=True),
        sa.Column("navigation_status", sa.Integer(), nullable=True),
        sa.Column("rate_of_turn", sa.Integer(), nullable=True),
        sa.Column("position_accuracy", sa.Integer(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mmsi"],
            ["ais.vessels.mmsi"],
            name=op.f("fk_vessel_positions_mmsi_vessels"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vessel_positions")),
        schema="ais",
    )
    op.create_index(
        "ix_vessel_positions_mmsi_timestamp",
        "vessel_positions",
        ["mmsi", "timestamp"],
        schema="ais",
    )
    op.create_index(
        "ix_vessel_positions_timestamp",
        "vessel_positions",
        ["timestamp"],
        schema="ais",
    )
    op.create_index(
        "ix_vessel_positions_position",
        "vessel_positions",
        ["position"],
        schema="ais",
        postgresql_using="gist",
    )

    # Create zones table
    op.create_table(
        "zones",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("zone_type", sa.String(length=50), nullable=False),
        sa.Column("security_level", sa.Integer(), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geography(
                geometry_type="POLYGON",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("alert_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("monitor_entries", sa.Boolean(), nullable=False),
        sa.Column("monitor_exits", sa.Boolean(), nullable=False),
        sa.Column("speed_limit_knots", sa.Float(), nullable=True),
        sa.Column(
            "time_restrictions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("display_color", sa.String(length=7), nullable=True),
        sa.Column("fill_opacity", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zones")),
        sa.UniqueConstraint("code", name=op.f("uq_zones_code")),
        schema="security",
    )
    op.create_index(
        "ix_zones_geometry",
        "zones",
        ["geometry"],
        schema="security",
        postgresql_using="gist",
    )
    op.create_index("ix_zones_zone_type", "zones", ["zone_type"], schema="security")
    op.create_index(
        "ix_zones_security_level", "zones", ["security_level"], schema="security"
    )
    op.create_index("ix_zones_active", "zones", ["active"], schema="security")

    # Create alerts table
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("vessel_mmsi", sa.String(length=9), nullable=True),
        sa.Column("secondary_vessel_mmsi", sa.String(length=9), nullable=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "position",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.String(length=255), nullable=True),
        sa.Column("acknowledgment_notes", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["vessel_mmsi"],
            ["ais.vessels.mmsi"],
            name=op.f("fk_alerts_vessel_mmsi_vessels"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["secondary_vessel_mmsi"],
            ["ais.vessels.mmsi"],
            name=op.f("fk_alerts_secondary_vessel_mmsi_vessels"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"],
            ["security.zones.id"],
            name=op.f("fk_alerts_zone_id_zones"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
        schema="security",
    )
    op.create_index(
        "ix_alerts_alert_type", "alerts", ["alert_type"], schema="security"
    )
    op.create_index("ix_alerts_severity", "alerts", ["severity"], schema="security")
    op.create_index("ix_alerts_status", "alerts", ["status"], schema="security")
    op.create_index(
        "ix_alerts_vessel_mmsi", "alerts", ["vessel_mmsi"], schema="security"
    )
    op.create_index(
        "ix_alerts_created_at", "alerts", ["created_at"], schema="security"
    )
    op.create_index(
        "ix_alerts_position",
        "alerts",
        ["position"],
        schema="security",
        postgresql_using="gist",
    )

    # Create alert_acknowledgments table
    op.create_table(
        "alert_acknowledgments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("user_name", sa.String(length=255), nullable=True),
        sa.Column("user_role", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("action_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["security.alerts.id"],
            name=op.f("fk_alert_acknowledgments_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_acknowledgments")),
        schema="security",
    )
    op.create_index(
        "ix_alert_acks_alert_id",
        "alert_acknowledgments",
        ["alert_id"],
        schema="security",
    )
    op.create_index(
        "ix_alert_acks_user_id",
        "alert_acknowledgments",
        ["user_id"],
        schema="security",
    )
    op.create_index(
        "ix_alert_acks_action",
        "alert_acknowledgments",
        ["action"],
        schema="security",
    )
    op.create_index(
        "ix_alert_acks_created_at",
        "alert_acknowledgments",
        ["created_at"],
        schema="security",
    )

    # Create system_config table
    op.create_table(
        "system_config",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "default_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("value_type", sa.String(length=50), nullable=False),
        sa.Column(
            "constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("editable", sa.Boolean(), nullable=False),
        sa.Column("requires_restart", sa.Boolean(), nullable=False),
        sa.Column("modified_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_config")),
        sa.UniqueConstraint("key", name=op.f("uq_system_config_key")),
        schema="security",
    )
    op.create_index(
        "ix_system_config_key",
        "system_config",
        ["key"],
        unique=True,
        schema="security",
    )
    op.create_index(
        "ix_system_config_category",
        "system_config",
        ["category"],
        schema="security",
    )
    op.create_index(
        "ix_system_config_active", "system_config", ["active"], schema="security"
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("system_config", schema="security")
    op.drop_table("alert_acknowledgments", schema="security")
    op.drop_table("alerts", schema="security")
    op.drop_table("zones", schema="security")
    op.drop_table("vessel_positions", schema="ais")
    op.drop_table("vessels", schema="ais")

    # Note: We don't drop schemas or extensions as they might be used by other things
