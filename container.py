from abc import ABC, abstractmethod
from typing import Type, Dict, Callable, TypeVar, TypeAlias, Any, Union, Tuple, Generic
from pydantic import BaseModel
from dataclasses import dataclass, field

class BaseResponse(BaseModel):
    response: str

# generic for services
TService = TypeVar('TService')

@dataclass
class ServiceSignature(Generic[TService]):
    ctor: Callable[..., TService] = field()
    args: Tuple[Any, ...] = field(default=None)
    kwargs: Dict[str, Any] = field(default=None)

    def new(self):
        return self.ctor(*self.args, **self.kwargs)
    
TransientsCache: TypeAlias = Dict[Type[Any], ServiceSignature[Any]]
SingletonsCache: TypeAlias = Dict[Type[Any], Any]

class DependencyContainer:
    def __init__(self) -> None:
        self._singletons: SingletonsCache = dict()
        self._transients: TransientsCache = dict()
        self._registrations = set()

    def _is_registered_interface(self, interface_type: Type[TService]) -> bool:
        return interface_type in self._registrations
    
    @classmethod
    def _typecheck(cls, interface_type: Type[TService], service: Union[TService, Callable[..., TService]]):
        return (callable(service) and issubclass(service, interface_type)) or type(service) == interface_type

    def add_singleton(
        self, 
        interface_type: Type[TService], 
        instance: TService=None,
        constructor: Callable[..., TService]=None, 
        /, 
        *args, 
        **kwargs
    ) -> None:
        if self._is_registered_interface(interface_type):
            # not typical, but we'll do it
            raise ValueError(f'{interface_type.__name__} already registered with this container.')
        elif instance:
            if not self._typecheck(interface_type, instance):
                raise TypeError(
                    f'Supplied instance is not dervied from interface type: '
                    f'{interface_type} ({type(instance)} != {interface_type})'
                )
            self._singletons[interface_type] = instance
        else:
            self._singletons[interface_type] = constructor(*args, **kwargs)

    def add_transient(
        self, 
        interface_type: Type[TService], 
        constructor: Callable[..., TService], 
        /, 
        *args, 
        **kwargs
    ) -> None:
        if self._is_registered_interface(interface_type):
            raise ValueError(f'{interface_type.__name__} already registered with this container.')
        elif not self._typecheck(interface_type, constructor):
            raise TypeError(
                f'Supplied type is not dervied from interface type: {interface_type}'
            )
        self._transients[interface_type] = ServiceSignature(constructor, args, kwargs)

    def get(self, interface: Type[TService]) -> TService:
        if interface in self._transients:
            service_factory: ServiceSignature[TService] = self._transients[interface]
            return service_factory.new()
        elif interface in self._singletons:
            return self._singletons[interface]
        else:
            raise KeyError(f"Service {interface} not found")