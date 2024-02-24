from typing import (
    Annotated,
    TypeVar,
    Generic, 
    Callable, 
)

from dataclasses import dataclass, field

from .types import TService

@dataclass
class ServiceSignature(Generic[TService]):
    """Encapsulates the constructor signature of a particular service that gets registerd with the container.

    Args:
        Generic (TService): Generically typed signature to TService
    """
    ctor: Annotated[
        Callable[..., TService], 
        field(metadata={'description': 'The service constructor.'})
    ]

    def new(self, *args, **kwargs) -> TService:
        """Constructs a new instance of the service which can be registered with the container.

        Returns:
            TService: A concrete instance of type `TService`
        """
        return self.ctor(*args, **kwargs)