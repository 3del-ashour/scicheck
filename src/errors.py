"""Project-wide error types."""


class SciCheckError(Exception):
    """Base error. Orchestrator catches these and degrades gracefully."""


class RAGError(SciCheckError):
    """Vector DB or embedding failure."""


class AgentError(SciCheckError):
    """Any agent runtime failure."""


class SafetyViolation(SciCheckError):
    """Raised by Safety Monitor when output cannot be made safe."""
