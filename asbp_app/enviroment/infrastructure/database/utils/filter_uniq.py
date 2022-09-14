from typing import Type, Union, Dict
from pydantic import BaseModel
from pqueue_app.enviroment.infrastructure.database.models import AbstractDbModel


def create_filters(model: Type[AbstractDbModel], data: Union[BaseModel, Dict]) -> Dict:
    if isinstance(data, BaseModel):
        data = data.dict()
    filters = {}
    if data.get("name"):  # tortoise has in model only related fields
        filters['name'] = data.get("name")
    if data.get("username"):  # tortoise has in model only related fields
        filters['username'] = data.get("username")
    if "company" in model._meta.fields:
        filters["company_id"] = data.get("company_id")
    if "office" in model._meta.fields:
        filters["office_id"] = data.get("office_id")
    if "service" in model._meta.fields:
        filters["service_id"] = data.get("service_id")
    return filters
