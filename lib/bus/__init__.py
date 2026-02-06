"""Message bus module for decoupled channel-agent communication."""

from lib.bus.events import InboundMessage, OutboundMessage
from lib.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
