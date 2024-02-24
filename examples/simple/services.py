from abc import ABC, abstractmethod

import fastdi

from dataclasses import dataclass

@dataclass
class MyConfiguration(object):

    a: int
    b: int

fastdi.add_configuration(MyConfiguration(1, 2))

class IService(ABC):
    @abstractmethod
    def get_message(self) -> str:
        ...

@fastdi.scoped
class MyTransientService(IService):

    def __init__(self, config: MyConfiguration):
        self.config = config

    def get_message(self) -> str:
        return f'Hello, World! {self.config.a} + {self.config.b} = {self.config.a + self.config.b}'