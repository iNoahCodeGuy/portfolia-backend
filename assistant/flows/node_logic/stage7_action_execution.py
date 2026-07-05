"""Action execution handlers for conversation side effects.

This module handles all side effects triggered by conversation actions:
- Sending resume emails via Resend
- Sending SMS notifications via Twilio
- Generating signed URLs for resume downloads
- Logging analytics events

Each action handler includes graceful degradation if services are unavailable.
"""

import logging
from typing import Dict, Any, Optional

from assistant.state.conversation_state import ConversationState
from assistant.services.resend_service import get_resend_service
from assistant.services.twilio_service import get_twilio_service

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes side-effect actions with lazy service initialization.

    This class manages service initialization and provides a clean interface
    for executing different action types. Services are only initialized when
    needed, and failures are logged without crashing the conversation flow.
    """

    def __init__(self):
        """Initialize with no services loaded."""
        self._resend_service: Optional[Any] = None
        self._twilio_service: Optional[Any] = None

    def reset_services(self) -> None:
        """Reset all cached services (used in testing).

        This allows tests to reinitialize services with mocked dependencies.
        """
        self._resend_service = None
        self._twilio_service = None

    def _ensure_resend(self) -> Optional[Any]:
        """Get or initialize Resend email service.

        Returns:
            Resend service instance or None if initialization failed.
        """
        if self._resend_service is None:
            try:
                self._resend_service = get_resend_service()
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Failed to initialize Resend service: %s", exc)
                self._resend_service = False
        return self._resend_service if self._resend_service is not False else None

    def _ensure_twilio(self) -> Optional[Any]:
        """Get or initialize Twilio SMS service.

        Returns:
            Twilio service instance or None if initialization failed.
        """
        if self._twilio_service is None:
            try:
                self._twilio_service = get_twilio_service()
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Failed to initialize Twilio service: %s", exc)
                self._twilio_service = False
        return self._twilio_service if self._twilio_service is not False else None

    def execute_notify_contact_request(self, state: ConversationState, action: Dict[str, Any]) -> None:
        """Send email and SMS notifications for contact requests.

        Args:
            state: Conversation state containing user contact info
            action: Action dictionary with optional urgent flag
        """
        contact_name = state.get("user_name", "there")
        contact_email = state.get("user_email")
        contact_phone = state.get("user_phone")
        query = state.get("query", "")
        message_preview = query[:120] if query else "No message"

        # Send email notification via Resend
        resend_service = self._ensure_resend()
        if resend_service and contact_email:
            resend_service.send_contact_notification(
                from_name=contact_name,
                from_email=contact_email,
                message=query,
                user_role=state["role"],
                phone=contact_phone,
            )

        # Send SMS notification via Twilio
        twilio_service = self._ensure_twilio()
        if twilio_service:
            twilio_service.send_contact_alert(
                from_name=contact_name,
                from_email=contact_email or "unknown@contact.com",
                message_preview=message_preview,
                is_urgent=action.get("urgent", False)
            )

    def execute_send_linkedin(self, state: ConversationState, action: Dict[str, Any]) -> None:
        """Log that LinkedIn profile was offered.

        Args:
            state: Conversation state
            action: Action dictionary (unused for this action type)
        """
        if "analytics_metadata" not in state:
            state["analytics_metadata"] = {}
        state["analytics_metadata"]["linkedin_offer"] = True

    def execute(self, state: ConversationState) -> ConversationState:
        """Execute all pending actions on the conversation state.

        Args:
            state: Conversation state with pending_actions list

        Returns:
            Updated conversation state
        """
        if not state.get("pending_actions"):
            return state

        for action in state["pending_actions"]:
            action_type = action.get("type")

            try:
                if action_type == "notify_contact_request":
                    self.execute_notify_contact_request(state, action)
                elif action_type == "send_linkedin":
                    self.execute_send_linkedin(state, action)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Action %s failed: %s", action_type, exc)

        return state


# Global executor instance (reused across requests for service caching)
_action_executor = ActionExecutor()


def execute_actions(state: ConversationState) -> ConversationState:
    """Execute all pending actions using the global executor.

    This is the main entry point used by conversation_nodes.py.

    Args:
        state: Conversation state with pending actions

    Returns:
        Updated conversation state after executing actions
    """
    return _action_executor.execute(state)
