"""Application-facing failures; adapters translate their concrete exceptions."""


class ApplicationError(Exception):
    """Base for execution failures, distinct from contract ValidationError."""


class ConfigurationError(ApplicationError):
    """Required execution configuration is missing or invalid."""


class ProviderUnavailableError(ApplicationError):
    """The configured model provider cannot serve the request."""


class AgentTimeoutError(ApplicationError):
    """The execution deadline was exceeded."""


class ProductRetrievalError(ApplicationError):
    """Catalog retrieval failed; an empty result is not this error."""


class AgentExecutionError(ApplicationError):
    """Agent execution failed for another reason."""


class AuthenticationError(ApplicationError):
    """A session/customer operation requires a valid trusted identity."""


class SessionAccessError(ApplicationError):
    """A session does not exist or is inaccessible to the caller."""


class SessionConflictError(ApplicationError):
    """A concurrent turn conflicts with the session state."""


class ConversationPersistenceError(ApplicationError):
    """Conversation storage could not complete an operation."""
