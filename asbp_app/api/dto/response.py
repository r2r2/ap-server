from typing import cast, Type, List

from pydantic import BaseModel as PdModel
from tortoise.contrib.pydantic import pydantic_model_creator
from web_foundation.environment.resources.database.models import AbstractDbModel
from web_foundation.utils.helpers import all_subclasses


def get_out_struct(db_model):
    out_struct = pydantic_model_creator(db_model, name=db_model.__name__, allow_cycles=False)
    return out_struct


def get_list_out_struct(pd_model):
    # --- Create list response (List[out_struct]) --- #
    lname = f"{pd_model.__name__}_list"
    properties = {"__annotations__": {"__root__": List[pd_model]}}  # type: ignore
    # Creating Pydantic class for the properties generated before
    return cast(Type[PdModel], type(lname, (PdModel,), properties))


db_model_responses = {}
for model in all_subclasses(AbstractDbModel):
    db_model_responses[model] = pydantic_model_creator(model, name=model.__name__)


class AuthResponse(PdModel):
    token: str
    session: int
    user_id: str


class ClaimUploadExcelResponse(PdModel):
    message: str


class WebPushNotifyAll(PdModel):
    status: str
    result: List[bool]
