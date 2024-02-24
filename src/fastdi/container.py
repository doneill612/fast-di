from typing import Type, TypeAlias, Union, Callable, Dict, Any

from .signature import ServiceSignature, TService
    
TransientsCache: TypeAlias = Dict[Type[Any], ServiceSignature[Any]]
SingletonsCache: TypeAlias = Dict[Type[Any], Any]

class DependencyContainer:

    def __init__(self) -> None:
        self._singletons: SingletonsCache = dict()
        self._transients: TransientsCache = dict()
        self._registrations = set()

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
        self._transients[interface_type] = ServiceSignature(constructor, args=args, kwargs=kwargs)        
        
    def inject(self, interface: Type[TService]) -> Callable[[], TService]:
        def resolve() -> TService:
            if interface in self._transients:
                signature: ServiceSignature[TService] = self._transients[interface]
                return signature.new()
            elif interface in self._singletons:
                return self._singletons[interface]
            else:
                raise KeyError(f"Service {interface} not found")
        return resolve
        
    def _is_registered_interface(self, interface_type: Type[TService]) -> bool:
        return interface_type in self._registrations
    
    @classmethod
    def _typecheck(cls, interface_type: Type[TService], service: Union[TService, Callable[..., TService]]):
        return (callable(service) and issubclass(service, interface_type)) or type(service) == interface_type