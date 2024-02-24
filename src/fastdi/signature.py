from typing import (
    Annotated,
    TypeVar,
    Optional,
    Generic, 
    Callable, 
    Dict, 
    Tuple, 
    Any
)

from dataclasses import dataclass, field


TService = TypeVar('TService')

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
    args: Annotated[
        Optional[Tuple[Any, ...]], 
        field(kw_only=True, default=None, metadata={'description': 'Positional constructor args for the service.'})
    ]
    kwargs: Annotated[
        Optional[Dict[str, Any]], 
        field(kw_only=True, default=None, metadata={'description': 'Keyword constructor args for the service.'})
    ]

    def new(self) -> TService:
        """Constructs a new instance of the service which can be registered with the container.

        Returns:
            TService: A concrete instance of type `TService`
        """
        return self.ctor(*self.args, **self.kwargs)