from contextvars import ContextVar, Token

correlation_id_context: ContextVar[str | None] = ContextVar(
    "geonex_correlation_id",
    default=None,
)

component_context: ContextVar[str | None] = ContextVar(
    "geonex_component",
    default=None,
)


def set_correlation_id(value: str | None) -> Token:
    return correlation_id_context.set(value)


def reset_correlation_id(token: Token) -> None:
    correlation_id_context.reset(token)


def set_component(value: str | None) -> Token:
    return component_context.set(value)


def reset_component(token: Token) -> None:
    component_context.reset(token)
