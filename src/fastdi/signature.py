from typing import (
    Annotated,
    Any,
    TypeVar,
    Generic, 
    Callable, 
)

from dataclasses import dataclass, field

D = TypeVar('D')

@dataclass
class Signature(Generic[D]):
    """Encapsulates the constructor signature of a particular service that gets registerd with the container.

    Args:
        Generic (D): Generically typed signature to D
    """
    constructor: Annotated[
        Callable[..., D], 
        field(metadata={'description': 'The service constructor.'})
    ]
    
    def __call__(self, *args: Any, **kwds: Any) -> D:
        return self.constructor(*args, **kwds)