from .container import ServiceProvider
from fastapi import FastAPI


def init(api: FastAPI) -> ServiceProvider:
    provider.initialize(api)

def transient(cls):
    return provider.transient(cls)

def singleton(cls):
    return provider.singleton(cls)

def inject(cls):
    return provider.inject(cls)

def add_configuration(configuration):
    return provider.add_configuration(configuration)

class __FastDI:

    def __init__(self):
        self._provider = ServiceProvider()

    @property
    def provider(self) -> ServiceProvider:
        return self._provider

__fastdi = __FastDI()

provider = __fastdi.provider

__all__ = [
    'provider',
    'init',
    'transient',
    'singleton'
    'inject'
]