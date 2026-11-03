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


class OperationalRetrievalError(ApplicationError):
    """Customer/order retrieval failed; never substitute an empty result."""


class PolicyRetrievalError(ApplicationError):
    """Policy search could not run; this is not evidence that the manual has no rule."""


class AgentExecutionError(ApplicationError):
    """Agent execution failed for another reason."""


class CustomerSelectionError(ApplicationError):
    """The selected demo customer is missing or unknown."""


class SessionAccessError(ApplicationError):
    """A session does not exist or is inaccessible to the caller."""


class SessionConflictError(ApplicationError):
    """A concurrent turn conflicts with the session state."""


class ConversationPersistenceError(ApplicationError):
    """Conversation storage could not complete an operation."""
