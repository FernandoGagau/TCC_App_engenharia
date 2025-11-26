"""
Domain Exceptions
Custom exceptions for domain layer
Following DDD principles
"""


class DomainException(Exception):
    """Base exception for domain layer"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class InvalidEntityStateException(DomainException):
    """Raised when entity is in invalid state for operation"""
    pass


class BusinessRuleViolationException(DomainException):
    """Raised when a business rule is violated"""
    pass


class EntityNotFoundException(DomainException):
    """Raised when entity is not found"""
    pass


class DuplicateEntityException(DomainException):
    """Raised when attempting to create duplicate entity"""
    pass


class InvalidValueObjectException(DomainException):
    """Raised when value object validation fails"""
    pass


class AggregateException(DomainException):
    """Raised when aggregate invariant is violated"""
    pass