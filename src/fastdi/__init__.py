from .dependency import DependencyContainer
from fastapi import FastAPI


def init(api: FastAPI) -> DependencyContainer:
    provider.initialize(api)

def scoped(cls):
    return provider.transient(cls)

def singleton(cls):
    return provider.singleton(cls)

def inject(cls):
    return provider.inject(cls)

def add_configuration(configuration):
    return provider.add_configuration(configuration)

class __FastDI:

    def __init__(self):
        self._provider = DependencyContainer()

    @property
    def provider(self) -> DependencyContainer:
        return self._provider

__fastdi = __FastDI()

provider = __fastdi.provider

__all__ = [
    'provider',
    'init',
    'scoped',
    'singleton'
    'inject'
]