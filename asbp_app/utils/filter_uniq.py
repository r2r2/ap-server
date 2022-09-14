from typing import Type, Union, Dict
from pydantic import BaseModel
from web_foundation.environment.resources.database.models import AbstractDbModel


def create_filters(model: Type[AbstractDbModel], data: Union[BaseModel, Dict]) -> Dict:
    if isinstance(data, BaseModel) or issubclass(data.__class__, BaseModel):
        data = data.dict()
    filters = {}
    if data.get("name"):  # tortoise has in model only related fields
        filters['name'] = data.get("name")
    if data.get("username"):  # tortoise has in model only related fields
        filters['username'] = data.get("username")
    return filters