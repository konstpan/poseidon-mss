"""AlertAcknowledgment model for tracking alert acknowledgment history."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.risk_alert import RiskAlert


class AlertAcknowledgment(Base):
    """Alert acknowledgment history model."""

    __tablename__ = "alert_acknowledgments"
    __table_args__ = (
        Index("ix_alert_acks_alert_id", "alert_id"),
        Index("ix_alert_acks_user_id", "user_id"),
        Index("ix_alert_acks_action", "action"),
        Index("ix_alert_acks_created_at", "created_at", postgresql_using="btree"),
        {"schema": "security"},
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.uuid_generate_v4(),
    )

    # Foreign key to alert
    alert_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("security.alerts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # User who performed the action
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Action type
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # Actions: acknowledged, resolved, dismissed, escalated, comment, reassigned

    # Previous status (for audit trail)
    previous_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Notes and comments
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional metadata
    action_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Example action_metadata:
    # {
    #     "ip_address": "192.168.1.100",
    #     "client_type": "web",
    #     "session_id": "abc123",
    #     "reason_code": "false_positive"
    # }

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )

    # Relationship to alert
    alert: Mapped["RiskAlert"] = relationship(
        "RiskAlert",
        back_populates="acknowledgments",
    )

    def __repr__(self) -> str:
        return f"<AlertAcknowledgment(id={self.id}, alert_id={self.alert_id}, action={self.action})>"

    @property
    def action_text(self) -> str:
        """Return human-readable action text."""
        actions = {
            "acknowledged": "Acknowledged",
            "resolved": "Resolved",
            "dismissed": "Dismissed",
            "escalated": "Escalated",
            "comment": "Comment Added",
            "reassigned": "Reassigned",
        }
        return actions.get(self.action, self.action.replace("_", " ").title())

    @classmethod
    def create_acknowledgment(
        cls,
        alert_id: UUID,
        user_id: str,
        action: str,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        notes: Optional[str] = None,
        user_name: Optional[str] = None,
        user_role: Optional[str] = None,
        action_metadata: Optional[dict[str, Any]] = None,
    ) -> "AlertAcknowledgment":
        """Factory method to create an acknowledgment record."""
        return cls(
            alert_id=alert_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            action_metadata=action_metadata,
        )
