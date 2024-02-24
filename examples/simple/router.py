from typing import Annotated

import fastdi
from fastapi import APIRouter, Depends
from .services import IService


router = APIRouter(prefix='/service')

@router.get('/')
def hello_world(service: Annotated[IService, Depends(fastdi.inject(IService))]):
    return service.get_message()