import inspect

from functools import wraps
from typing import Type, Union, Callable, Dict, Any, Generic, overload 

from fastapi import FastAPI, Request

from .signature import ServiceSignature
from .types import TService, TConfiguration, TDependency


class Dependency(Generic[TDependency]):

    def __init__(self, service_provider: 'ServiceProvider', interface_type: Type[TDependency]) -> None:
        self._provider = service_provider
        self._interface_type = interface_type

    def __call__(self, request: Request) -> TDependency:
        provider: ServiceProvider = request.app.state.service_provider
        return provider.resolve(self._interface_type)

class ServiceProvider:
    """The service provider. Maintains a list of dependencies and provides instances to 
    API routes when requested.

    A service can be registered as a singleton or scoped. Singleton instances are shared between 
    all requests, where scoped instances are instantiated for every request.

    Configurations are singletons which are required by services.
    """
    def __init__(self) -> None:
        self._init: bool = False
        self._singletons: Dict[Type[Any], Union[ServiceSignature[Any], Any]] = dict()
        self._transients: Dict[Type[Any], ServiceSignature[Any]] = dict()
        self._configs: Dict[Type[Any], Union[ServiceSignature[Any], Any]] = dict()
        self._container: Dict[Type[Any], Dependency] = {}

    @property
    def is_initialized(self) -> bool:
        """Whether or not the container has been linked to a FastAPI instance.
        """
        return self._init

    def initialize(self, api: FastAPI):
        """Registers this service provider with a FastAPI instance.

        Args:
            api (FastAPI): The FastAPI instance
        """
        if not self.is_initialized:
            api.state.service_provider = self
            self._init = True

    def add_configuration(self, pattern: TConfiguration):
        """Registers a configuration singleton to the SP's container.

        Args:
            pattern (TConfiguration): A configuration instance

        Raises:
            ValueError: If a configuration of type `TConfiguration` has already been registered with the container.
        """
        configuration_type = type(pattern)
        if configuration_type in self._configs:
            raise ValueError(f'{configuration_type.__name__} already registered with this container.')
        self._configs[configuration_type] = pattern
        self._container[configuration_type] = Dependency(self, configuration_type)

    @overload
    def add_singleton(self, interface_type: Type[TService], pattern: TService) -> None:
        ...

    @overload
    def add_singleton(self, interface_type: Type[TService], pattern: Callable[..., TService]) -> None:
        ...

    def add_singleton(
        self, 
        interface_type: Type[TService], 
        pattern: Union[TService, Callable[..., TService]],
    ) -> None:
        """Registers a service as a singleton with the SP's container.

        Singletons are re-used for all requests.

        Args:
            interface_type (Type[TService]): The supertype of the service.
            pattern (Union[TService, Callable[..., TService]]): Either a concrete instance, or a factory (Type[`TService`])

        Raises:
            ValueError: If a `TService` singleton service is already registered.
            TypeError: If the supplied instance or factory does not inherit from the `TService` interface
        """
        if self._registered(interface_type):
            # not typical, but we'll do it
            raise ValueError(f'{interface_type.__name__} already registered with this container.')
        valid, is_callable = self._typecheck(interface_type, pattern)
        if not valid:
            raise TypeError(
                f'Supplied instantiation pattern or instance is not compatible with interface type: {interface_type.__name__}'
            )
        self._singletons[interface_type] = ServiceSignature(pattern) if is_callable else pattern
        self._container[interface_type] = Dependency(self, interface_type)

    def add_transient(
        self, 
        interface_type: Type[TService], 
        pattern: Callable[..., TService], 
    ) -> None:
        """Registers a scoped service with the SP's container.

        Scoped services are instantiated with every request.

        Args:
            interface_type (Type[TService]): The supertype of the service.
            pattern (Callable[..., TService]): Factory/constructor signature for the service being registered

        Raises:
            ValueError: If a `TService` scoped service is already registered.
            TypeError: If the supplied factory does not produce an object that inherits from the `TService` interface
        """
        if self._registered(interface_type):
            raise ValueError(f'{interface_type.__name__} already registered with this container.')
        elif not self._typecheck(interface_type, pattern)[0]:
            raise TypeError(
                f'Supplied type is not dervied from interface type: {interface_type}'
            )
        self._transients[interface_type] = ServiceSignature(pattern)
        self._container[interface_type] = Dependency(self, interface_type)    
        
    def inject(self, interface_type: Type[TService]) -> Dependency:
        """Fetches either a signature for a service or configuration, or the singleton instance 
        of an already-existing singleton service or configuration.

        Args:
            interface_type (Type[TService]): The interface type

        Returns:
            Dependency: A Dependency wrapper around the instance or signature
        """
        return self._container[interface_type]
    
    def resolve(
        self, 
        interface_type: Union[Type[TService], Type[TConfiguration]],
        *,
        caller: str=None,
    ) -> Union[TService, TConfiguration]:
        if not self.is_initialized:
            raise ValueError(
                'ServiceProvider is not initialized. Make sure to call '
                'fastdi.init(...) on your FastAPI object.'
            )
        if not self._registered(interface_type):
            msg = f'{interface_type} not registered with this container'
            if caller:
                msg = (
                    f'{msg} but is a required dependency for {caller}. Make sure to '
                    f'register {interface_type} as a configuration, singleton, or transient.'
                )
            else:
                msg += '.'
            raise ValueError(msg)
        if interface_type in self._transients:
            pattern = self._transients[interface_type]
            signature = inspect.signature(pattern.ctor).parameters
            signature = {
                name: self.resolve(param.annotation, caller=interface_type.__name__)
                for name, param in signature.items()
            }
            return pattern.new(**signature)
        elif interface_type in self._singletons:
            pattern = self._singletons[interface_type]
            if isinstance(pattern, ServiceSignature):
                signature = inspect.signature(pattern.ctor).parameters
                signature = {
                    name: self.resolve(param.annotation, caller=interface_type.__name__)
                    for name, param in signature.items()
                }
                instance = pattern.new(**signature)
                self._singletons[interface_type] = instance
                return instance
            else:
                return pattern
        elif interface_type in self._configs:
            return self._configs[interface_type]
            
    def singleton(self, cls: Type[TService]):
        return self._mark('singleton')(cls)
    
    def transient(self, cls: Type[TService]):
        return self._mark('transient')(cls)
    
    def _mark(self, registration_type: str):
        def class_dec(cls: Type[TService]):
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
            interface_type in self._transients or
            interface_type in self._singletons or
            interface_type in self._configs
        )
    
    @classmethod
    def _typecheck(cls, interface_type: Type[TService], service: Union[TService, Callable[..., TService]]):
        is_signature = callable(service)
        valid = issubclass(service, interface_type)
        return valid, is_signature
    
    