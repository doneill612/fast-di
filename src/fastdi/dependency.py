import inspect
import abc

from enum import Enum
from typing import Type, TypeAlias, TypeVar, Union, Callable, Dict, Any, Generic, overload 

from fastapi import FastAPI, Request

from .signature import Signature

T = TypeVar('T')

SingletonPattern: TypeAlias = Union[Signature[Any], Any]
TransientPattern: TypeAlias = Signature[Any]
Pattern: TypeAlias = Union[SingletonPattern, TransientPattern]

SingletonCache: TypeAlias = Dict[Type[Any], SingletonPattern]
TransientCache: TypeAlias = Dict[Type[Any], TransientPattern]



class Scope(str, Enum):
    SINGLETON = 'singleton'
    TRANSIENT = 'transient'


class DependencyContainer:
    def __init__(self) -> None:
        self.singletons: Dict[Type[Any], Dependency] = dict()
        self.configs: Dict[Type[Any], Dependency] = dict()
        self.transients: Dict[Type[Any], Dependency] = dict()
        self._init: bool = False

    @property
    def is_initialized(self) -> bool:
        return self._init

    def initialize(self, api: FastAPI):
        if not self.is_initialized:
            api.state.service_provider = self
            self._init = True

    def add_configuration(self, pattern: T):
        configuration_type = type(pattern)
        if configuration_type in self.configs:
            raise ValueError(f'{configuration_type.__name__} already registered with this container.')
        self.configs[configuration_type] = Dependency(configuration_type, pattern, Scope.SINGLETON)

    @overload
    def add_singleton(self, interface_type: Type[T], pattern: T) -> None:
        ...

    @overload
    def add_singleton(self, interface_type: Type[T], pattern: Callable[..., T]) -> None:
        ...

    def add_singleton(
        self, 
        interface_type: Type[T], 
        pattern: Union[T, Callable[..., T]],
    ) -> None:
        if self._registered(interface_type):
            # not typical, but we'll do it
            raise ValueError(f'{interface_type.__name__} already registered with this container.')
        valid, is_callable = self._typecheck(interface_type, pattern)
        if not valid:
            raise TypeError(
                f'Supplied instantiation pattern or instance is not compatible with interface type: {interface_type.__name__}'
            )
        self.singletons[interface_type] = Dependency(interface_type, Signature[T](pattern) if is_callable else pattern, Scope.SINGLETON)

    def add_transient(
        self, 
        interface_type: Type[T], 
        pattern: Callable[..., T], 
    ) -> None:
        if self._registered(interface_type):
            raise ValueError(f'{interface_type.__name__} already registered with this container.')
        elif not self._typecheck(interface_type, pattern)[0]:
            raise TypeError(
                f'Supplied type is not dervied from interface type: {interface_type}'
            )
        self.transients[interface_type] = Dependency(interface_type, Signature[T](pattern), Scope.TRANSIENT)
        
    def inject(self, interface_type: Type[T]) -> 'Dependency':
        if interface_type in self.transients:
            return self.transients[interface_type]
        elif interface_type in self.singletons:
            return self.singletons[interface_type]
        elif interface_type in self.configs:
            return self.configs[interface_type]
        else:
            raise ValueError
    
    def resolve(
        self, 
        interface_type: Type[T],
        *,
        caller: str=None,
    ) -> T:
        if not self.is_initialized:
            raise ValueError(
                'ServiceProvider is not initialized. Make sure to call '
                'fastdi.init(...) on your FastAPI object.'
            )
        if not self._registered(interface_type):
            msg = f'{interface_type.__name__} not registered with this container'
            if caller:
                msg = (
                    f'{msg} but is a required dependency for {caller}. Make sure to '
                    f'register {interface_type.__name__} as a configuration, singleton, '
                    'or transient.'
                )
            else:
                msg += '.'
            raise ValueError(msg)
        if interface_type in self.transients:
            return self.transients[interface_type].resolver(self).resolve(interface_type)
        elif interface_type in self.singletons:
            return self.singletons[interface_type].resolver(self).resolve(interface_type)
        elif interface_type in self.configs:
            return self.configs[interface_type].resolver(self).resolve(interface_type)
            
    def singleton(self, cls: Type[T]):
        return self._mark('singleton')(cls)
    
    def transient(self, cls: Type[T]):
        return self._mark('transient')(cls)
    
    def _mark(self, registration_type: str):
        def class_dec(cls: Type[T]):
            base = cls.__bases__[0]
            if registration_type == 'singleton':
                self.add_singleton(base if base != object else cls, cls)
            elif registration_type == 'transient':
                self.add_transient(base if base != object else cls, cls)
            else:
                raise ValueError('Unknown registration type')
            return cls
        return class_dec
        
    def _registered(self, interface_type):
        return (
            interface_type in self.transients or
            interface_type in self.singletons or
            interface_type in self.configs
        )
    
    @classmethod
    def _typecheck(cls, interface_type: Type[T], service: Union[T, Callable[..., T]]):
        is_signature = callable(service)
        valid = issubclass(service, interface_type)
        return valid, is_signature
    
class Dependency(Generic[T]):

    def __init__(self, interface_type: Type[T], pattern: Pattern, scope: Scope) -> None:
        self.interface_type = interface_type
        self.pattern = pattern
        self.scope = scope

    def __call__(self, request: Request) -> T:
        container: DependencyContainer = request.app.state.service_provider
        return self.resolver(container).resolve(self.interface_type)
    
    def resolver(self, container: 'DependencyContainer') -> 'Resolver':
        return Resolver.get_resolver(container, self.scope)
    

class Resolver(abc.ABC, Generic[T]):

    def __init__(self, container: 'DependencyContainer'):
        self.container = container

    @abc.abstractmethod
    def resolve(self, interface_type: Type[T]) -> T:
        ...

    @staticmethod
    def get_resolver(container: 'DependencyContainer', scope: Scope):
        if scope == Scope.SINGLETON:
            return SingletonResolver(container)
        else:
            return TransientResolver(container)


class SingletonResolver(Resolver, Generic[T]):
    def __init__(self, container: 'DependencyContainer'):
        super().__init__(container)
    
    def resolve(self, interface_type: Type[T]) -> T:
        if interface_type in self.container.singletons:
            dependency = self.container.singletons[interface_type]
        else:
            dependency = self.container.configs[interface_type]
        if isinstance(dependency.pattern, Signature):
            signature = inspect.signature(dependency.pattern.constructor).parameters
            signature = {
                name: self.container.resolve(param.annotation, caller=interface_type.__name__)
                for name, param in signature.items()
            }
            instance = dependency.pattern(**signature)
            self.container.singletons[interface_type] = instance
            return instance
        else:
            return dependency.pattern


class TransientResolver(Resolver, Generic[T]):
    def __init__(self, container: 'DependencyContainer'):
        super().__init__(container)

    def resolve(self, interface_type: Type[T]) -> T:
        dependency = self.container.transients[interface_type]
        signature = inspect.signature(dependency.pattern.constructor).parameters
        signature = {
            name: self.container.resolve(param.annotation, caller=interface_type.__name__)
            for name, param in signature.items()
        }
        return dependency.pattern(**signature)