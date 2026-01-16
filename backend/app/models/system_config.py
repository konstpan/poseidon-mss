"""SystemConfig model for storing system configuration values."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base, TimestampMixin


class SystemConfig(Base, TimestampMixin):
    """System configuration storage model."""

    __tablename__ = "system_config"
    __table_args__ = (
        Index("ix_system_config_key", "key", unique=True),
        Index("ix_system_config_category", "category"),
        Index("ix_system_config_active", "active"),
        {"schema": "security"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Configuration key (unique identifier)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Category for grouping related configs
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="general",
    )
    # Categories: alert_thresholds, risk_scoring, ais_processing,
    #             notification, system, display

    # Human-readable name and description
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration value (JSONB for flexible types)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)

    # Default value for reference
    default_value: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # Value type for validation
    value_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="string",
    )
    # Types: string, integer, float, boolean, json, array

    # Validation constraints (JSONB)
    constraints: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Example constraints:
    # {
    #     "min": 0,
    #     "max": 100,
    #     "enum": ["option1", "option2"],
    #     "pattern": "^[a-z]+$"
    # }

    # Whether this config is active
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Whether this config can be modified through the UI
    editable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Whether this config requires a restart to take effect
    requires_restart: Mapped[bool] = mapped_column(Boolean, default=False)

    # Last modified by
    modified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.key}, value={self.value})>"

    @classmethod
    def get_default_configs(cls) -> list[dict[str, Any]]:
        """Return default system configuration values."""
        return [
            # Alert Thresholds
            {
                "key": "alert.speed_violation_threshold",
                "category": "alert_thresholds",
                "name": "Speed Violation Threshold",
                "description": "Speed threshold (knots) for triggering speed violation alerts in restricted zones",
                "value": 10.0,
                "default_value": 10.0,
                "value_type": "float",
                "constraints": {"min": 0, "max": 50},
            },
            {
                "key": "alert.ais_gap_threshold_minutes",
                "category": "alert_thresholds",
                "name": "AIS Gap Threshold",
                "description": "Minutes without AIS signal before triggering gap alert",
                "value": 30,
                "default_value": 30,
                "value_type": "integer",
                "constraints": {"min": 5, "max": 1440},
            },
            {
                "key": "alert.collision_risk_distance_nm",
                "category": "alert_thresholds",
                "name": "Collision Risk Distance",
                "description": "Distance in nautical miles for collision risk detection",
                "value": 0.5,
                "default_value": 0.5,
                "value_type": "float",
                "constraints": {"min": 0.1, "max": 5.0},
            },
            {
                "key": "alert.anchor_drag_threshold_meters",
                "category": "alert_thresholds",
                "name": "Anchor Drag Threshold",
                "description": "Distance in meters before anchor drag alert is triggered",
                "value": 50,
                "default_value": 50,
                "value_type": "integer",
                "constraints": {"min": 10, "max": 500},
            },
            # Risk Scoring
            {
                "key": "risk.dark_vessel_score",
                "category": "risk_scoring",
                "name": "Dark Vessel Risk Score",
                "description": "Base risk score for vessels with AIS gaps",
                "value": 30,
                "default_value": 30,
                "value_type": "integer",
                "constraints": {"min": 0, "max": 100},
            },
            {
                "key": "risk.restricted_zone_entry_score",
                "category": "risk_scoring",
                "name": "Restricted Zone Entry Score",
                "description": "Risk score addition for entering restricted zones",
                "value": 25,
                "default_value": 25,
                "value_type": "integer",
                "constraints": {"min": 0, "max": 100},
            },
            {
                "key": "risk.suspicious_pattern_score",
                "category": "risk_scoring",
                "name": "Suspicious Pattern Score",
                "description": "Risk score for suspicious movement patterns",
                "value": 20,
                "default_value": 20,
                "value_type": "integer",
                "constraints": {"min": 0, "max": 100},
            },
            {
                "key": "risk.decay_rate_per_hour",
                "category": "risk_scoring",
                "name": "Risk Score Decay Rate",
                "description": "Points per hour that risk score decays when no incidents",
                "value": 2.0,
                "default_value": 2.0,
                "value_type": "float",
                "constraints": {"min": 0, "max": 10},
            },
            # AIS Processing
            {
                "key": "ais.position_update_interval_seconds",
                "category": "ais_processing",
                "name": "Position Update Interval",
                "description": "Minimum seconds between storing vessel positions",
                "value": 60,
                "default_value": 60,
                "value_type": "integer",
                "constraints": {"min": 10, "max": 300},
            },
            {
                "key": "ais.track_history_hours",
                "category": "ais_processing",
                "name": "Track History Duration",
                "description": "Hours of vessel track history to display on map",
                "value": 24,
                "default_value": 24,
                "value_type": "integer",
                "constraints": {"min": 1, "max": 168},
            },
            # Notification Settings
            {
                "key": "notification.websocket_enabled",
                "category": "notification",
                "name": "WebSocket Notifications",
                "description": "Enable real-time WebSocket notifications",
                "value": True,
                "default_value": True,
                "value_type": "boolean",
            },
            {
                "key": "notification.email_enabled",
                "category": "notification",
                "name": "Email Notifications",
                "description": "Enable email notifications for critical alerts",
                "value": False,
                "default_value": False,
                "value_type": "boolean",
            },
            {
                "key": "notification.alert_cooldown_minutes",
                "category": "notification",
                "name": "Alert Cooldown Period",
                "description": "Minutes before same alert type can trigger again for same vessel",
                "value": 15,
                "default_value": 15,
                "value_type": "integer",
                "constraints": {"min": 1, "max": 60},
            },
            # Display Settings
            {
                "key": "display.map_center_lat",
                "category": "display",
                "name": "Default Map Center Latitude",
                "description": "Default map center latitude (Thessaloniki)",
                "value": 40.6401,
                "default_value": 40.6401,
                "value_type": "float",
            },
            {
                "key": "display.map_center_lon",
                "category": "display",
                "name": "Default Map Center Longitude",
                "description": "Default map center longitude (Thessaloniki)",
                "value": 22.9444,
                "default_value": 22.9444,
                "value_type": "float",
            },
            {
                "key": "display.default_zoom",
                "category": "display",
                "name": "Default Map Zoom",
                "description": "Default map zoom level",
                "value": 12,
                "default_value": 12,
                "value_type": "integer",
                "constraints": {"min": 1, "max": 20},
            },
        ]

    def validate_value(self, new_value: Any) -> tuple[bool, Optional[str]]:
        """Validate a new value against constraints."""
        if self.constraints is None:
            return True, None

        if "min" in self.constraints and new_value < self.constraints["min"]:
            return False, f"Value must be >= {self.constraints['min']}"

        if "max" in self.constraints and new_value > self.constraints["max"]:
            return False, f"Value must be <= {self.constraints['max']}"

        if "enum" in self.constraints and new_value not in self.constraints["enum"]:
            return False, f"Value must be one of: {self.constraints['enum']}"

        return True, None
