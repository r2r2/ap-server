import inspect
import re
from copy import copy, deepcopy
from functools import wraps

import sanic_ext
from sanic_ext.extensions.openapi.types import Schema, Array

from asbp_app.api.dto import access as access_dto
from asbp_app.api.dto import service as service_dto
from asbp_app.api.dto import response as response_dto
from asbp_app.api.protectors import user_protector
from asbp_app.api.views import access as access_view
from asbp_app.api.views import auth as auth_view
from asbp_app.api.views import claim as claim_view
from asbp_app.api.views import web_push as web_push_view
from asbp_app.api.views import visitor as visitor_view
from asbp_app.api.views import views_pass as pass_view
from asbp_app.api.views.auth import auth_response_fabric
from asbp_app.enviroment.infrastructure.database import models

params_filters = {
    "not": Schema(description="not definition", type="string"),

    "in": Array(Schema(description="any field value", type="string"),
                description="checks if value of field is in passed list"),

    "not_in": Array(Schema(description="any field value", type="string"),
                    description="not in definition"),

    "gte": Schema(description="greater or equals than passed value", type="string"),

    "gt": Schema(description="greater than passed value", type="string"),

    "lte": Schema(description="lower or equals than passed value", type="string"),

    "lt": Schema(description="lower than passed value", type="string"),

    "range": Array(Schema(description="any field value", type="string"),
                   description="between and given two values",
                   maxItems=2, minItems=2),

    "isnull": Schema(description="field is null", type="boolean"),

    "not_isnull": Schema(description="field is not null", type="boolean"),

    "contains": Schema(description="field contains specified substring", type="string"),

    "icontains": Schema(description="case insensitive contains", type="string"),

    "startswith": Schema(description="if field starts with value", type="string"),

    "istartswith": Schema(description="case insensitive startswith", type="string"),

    "endswith": Schema(description="if field ends with value", type="string"),

    "iendswith": Schema(description="case insensitive endswith", type="string"),

    "iexact": Schema(description="case insensitive equals", type="string"),
}

access_endpoints = {
    '/users': {
        'v1': {
            'handler': access_view.access_system_user,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.SystemUser.UpdateDto},
            'post': {'in_dto': access_dto.SystemUser.CreationDto},
            'delete': {}
        },
    },
    '/zones': {
        'v1': {
            'handler': access_view.access_zone,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.Zone.UpdateDto},
            'post': {'in_dto': access_dto.Zone.CreationDto},
            'delete': {}
        },
    },
    '/claims': {
        'v1': {
            'handler': access_view.access_claim,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.Claim.UpdateDto},
            'post': {'in_dto': access_dto.Claim.CreationDto},
            'delete': {}
        },
    },
    '/claimways': {
        'v1': {
            'handler': access_view.access_claim_way,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.ClaimWay.UpdateDto},
            'post': {'in_dto': access_dto.ClaimWay.CreationDto},
            'delete': {}
        },
    },
    '/claimtozones': {
        'v1': {
            'handler': access_view.access_claim_to_zone,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.ClaimToZone.UpdateDto},
            'post': {'in_dto': access_dto.ClaimToZone.CreationDto},
            'delete': {}
        },
    },
    '/parkingplaces': {
        'v1': {
            'handler': access_view.access_parking_place,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.ParkingPlace.UpdateDto},
            'post': {'in_dto': access_dto.ParkingPlace.CreationDto},
            'delete': {}
        },
    },
    # '/parkingplaces/mass-create-delete': {
    #     'v1': {
    #         'handler': access_view.access_parking_place_bulk,
    #         'protector': user_protector,
    #         'get': {},
    #         'post': {'in_dto': access_dto.ParkingPlace.BulkCreateDto},
    #         'delete': {}
    #     },
    # },
    '/parkings': {
        'v1': {
            'handler': access_view.access_parking,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.Parking.UpdateDto},
            'post': {'in_dto': access_dto.Parking.CreationDto},
            'delete': {}
        },
    },
    '/passes': {
        'v1': {
            'handler': access_view.access_pass,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.PassDto.UpdateDto},
            'post': {'in_dto': access_dto.PassDto.CreationDto},
            'delete': {}
        },
    },
    '/role': {
        'v1': {
            'handler': access_view.access_role,
            'protector': user_protector,
            'get': {}
        },
    },
    '/role_group': {
        'v1': {
            'delete': {'handler': access_view.access_role_group,
                       'protector': user_protector},
            'get': {'handler': access_view.access_role_group,
                    'protector': user_protector},
            'patch': {'handler': access_view.access_role_group,
                      'protector': user_protector,
                      'in_dto': access_dto.RoleGroup.UpdateDto},
            'post': {'handler': access_view.access_role_group,
                     'protector': user_protector,
                     'in_dto': access_dto.RoleGroup.CreationDto}
        }, },
    '/buildings': {
        'v1': {
            'handler': access_view.access_building,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.BuildingDto.UpdateDto},
            'post': {'in_dto': access_dto.BuildingDto.CreationDto},
            'delete': {}
        },
    },
    '/divisions': {
        'v1': {
            'handler': access_view.access_division,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.DivisionDto.UpdateDto},
            'post': {'in_dto': access_dto.DivisionDto.CreationDto},
            'delete': {}
        },
    },
    '/organisations': {
        'v1': {
            'handler': access_view.access_organization,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.OrganisationDto.UpdateDto},
            'post': {'in_dto': access_dto.OrganisationDto.CreationDto},
            'delete': {}
        },
    },
    '/job-titles': {
        'v1': {
            'handler': access_view.access_job_title,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.JobTitleDto.UpdateDto},
            'post': {'in_dto': access_dto.JobTitleDto.CreationDto},
            'delete': {}
        },
    },
    "/visitor/document/passport": {
        'v1': {
            'handler': access_view.access_document,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.PassportDto.UpdateDto},
            'post': {'in_dto': access_dto.PassportDto.CreationDto},
            'delete': {}
        },
    },
    "/visitor/document/international_passport": {
        'v1': {
            'handler': access_view.access_document,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.InternationalPassportDto.UpdateDto},
            'post': {'in_dto': access_dto.InternationalPassportDto.CreationDto},
            'delete': {}
        },
    },
    "/visitor/document/drive_licence": {
        'v1': {
            'handler': access_view.access_document,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.DriveLicenseDto.UpdateDto},
            'post': {'in_dto': access_dto.DriveLicenseDto.CreationDto},
            'delete': {}
        },
    },
    "/visitor/document/military_id": {
        'v1': {
            'handler': access_view.access_document,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.MilitaryIdDto.UpdateDto},
            'post': {'in_dto': access_dto.MilitaryIdDto.CreationDto},
            'delete': {}
        },
    },
    "/transports": {
        'v1': {
            'handler': access_view.access_transport,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.TransportDto.UpdateDto},
            'post': {'in_dto': access_dto.TransportDto.CreationDto},
            'delete': {}
        },
    },
    "/blacklists": {
        'v1': {
            'handler': access_view.access_black_list,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.BlackListDto.UpdateDto},
            'post': {'in_dto': access_dto.BlackListDto.CreationDto},
            'delete': {}
        },
    },
    "/settings": {
        'v1': {
            'handler': access_view.access_system_settings,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.SystemSettings.UpdateDto}
        },
    },
    "/wp/subscription": {
        'v1': {
            'handler': access_view.access_system_settings,
            'protector': user_protector,
            'get': {},
            'post': {'in_dto': access_dto.WebPush.CreationDto}
        },
    },
    "/stranger-things": {
        'v1': {
            'handler': access_view.access_stranger_things,
            'protector': user_protector,
            'get': {},
        },
    },
    "/watermarks": {
        'v1': {
            'handler': access_view.access_watermark,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.WaterMarkDto.UpdateDto},
            'post': {'in_dto': access_dto.WaterMarkDto.CreationDto},
            'delete': {}
        },
    },
    "/visitors": {
        'v1': {
            'handler': access_view.access_visitor,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.VisitorPhotoDto.UpdateDto},
            'post': {'in_dto': access_dto.VisitorPhotoDto.CreationDto},
            'delete': {},
        },
    },
    "/visitor/photos": {
        'v1': {
            'handler': access_view.access_visitor_photo,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.VisitorPhotoDto.UpdateDto},
            'post': {'in_dto': access_dto.VisitorPhotoDto.CreationDto},
            'delete': {},
        },
    },
    "/visitor/session": {
        'v1': {
            'handler': access_view.access_visitor_session,
            'protector': user_protector,
            'get': {},
            'patch': {'in_dto': access_dto.VisitSession.UpdateDto},
            'post': {'in_dto': access_dto.VisitSession.CreationDto},
            'delete': {},
        },
    },
}

for endpoint, versions in deepcopy(access_endpoints).items():
    for version, params in deepcopy(versions).items():
        endpoint_handler = params.get("handler")
        endpoint_protector = params.get("protector")
        endpoint_response_fabric = params.get("response_fabric")
        access_endpoints[endpoint][version].update({'scope': 'access'})
        for method_name, param in deepcopy(params).items():
            if not isinstance(param, dict):
                continue
            target_func = param.get('handler')
            target_func = target_func if target_func else endpoint_handler
            method_protector = param.get("protector")
            method_protector = method_protector if method_protector else endpoint_protector
            if param.get('out_dto'):
                out_struct = param.get('out_dto')
            else:
                # get out_struct from model name (in exec_access args)
                func_text = inspect.getsource(target_func)
                model_name = re.findall(r"context, (\w*)", func_text)
                if model_name:
                    model = getattr(models, model_name[0])
                    out_struct = response_dto.db_model_responses.get(model)
                    if not out_struct:
                        out_struct = response_dto.get_out_struct(model)
                    access_endpoints[endpoint][version][method_name]['out_dto'] = out_struct
                    param['out_dto'] = out_struct
                else:
                    out_struct = None

            # add routes with <entity_id>
            if method_name in ['patch', 'delete', 'get']:
                if method_name != 'get':
                    access_endpoints[endpoint][version].pop(method_name)
                if not access_endpoints.get(f"{endpoint}/<entity_id:int>"):
                    access_endpoints.update({f"{endpoint}/<entity_id:int>": {}})

                if not access_endpoints[f"{endpoint}/<entity_id:int>"].get(version):
                    access_endpoints[f"{endpoint}/<entity_id:int>"].update({
                        version: {
                            'handler': endpoint_handler,
                            'protector': endpoint_protector,
                            'response_fabric': endpoint_response_fabric
                        }
                    })
                access_endpoints[f"{endpoint}/<entity_id:int>"][version].update({method_name: copy(param)})

                if method_name == 'get' and out_struct:
                    access_endpoints[endpoint][version][method_name]['out_dto'] = response_dto.get_list_out_struct(
                        out_struct)
                if not access_endpoints[endpoint].get(version):
                    access_endpoints[endpoint].pop(version)


            def new_wrap(func):  # wrapper to change handler signature (need for openapi)
                @wraps(func)
                def wr(*args, **kwargs):
                    return func(*args, **kwargs)

                return wr


            if method_name == 'get' and 'entity_id' not in endpoint and out_struct:
                get_access_func = new_wrap(target_func)
                get_access_func.__name__ = f"{get_access_func.__name__}__read"
                for field_model in out_struct.__fields__.values():
                    for filter, schema in params_filters.items():
                        schema.type = str
                        schema.example = f"{field_model.name}__{filter}"
                        get_access_func = sanic_ext.openapi.parameter(
                            name=f"{field_model.name}__{filter}", schema=schema)(get_access_func)
                access_endpoints[endpoint][version][method_name]['handler'] = get_access_func

service_endpoints = {
    "/claims/<claim_id:int>/approve": {
        'v1': {
            'patch': {
                'protector': user_protector,
                'handler': claim_view.claim_approve_handler,
                'in_dto': service_dto.ClaimDto.ApproveDto,
                'out_dto': response_dto.db_model_responses[models.ClaimWayApproval],
            },
        },
    },
    "/claims/upload-excel": {
        'v1': {
            'handler': claim_view.claim_excel_handler,
            'protector': user_protector,
            'get': {},
            'post': {
                'in_dto': service_dto.ClaimDto.GroupVisitDto,
                'out_dto': response_dto.ClaimUploadExcelResponse,
            },
        },
    },
    "/wp/notify-all": {
        'v1': {
            'post': {
                'protector': user_protector,
                'handler': web_push_view.notify_all_handler,
                'in_dto': service_dto.WebPush.NotifyAllDto,
                'out_dto': response_dto.WebPushNotifyAll,
            },
        },
    },
    "/visitors/<visitor_id:int>/visit-info": {
        'v1': {
            'get': {
                'protector': user_protector,
                'handler': visitor_view.get_visit_info,
                'in_dto': service_dto.WebPush.NotifyAllDto,
                'out_dto': None,
            },
        },
    },
    "/passes/<entity:int>/qr-code": {
        'v1': {
            'get': {
                'protector': user_protector,
                'handler': pass_view.create_qr_code,
                'in_dto': None,
                'out_dto': None,
            },
        },
    },
    "/passes/<entity:int>/bar-code": {
        'v1': {
            'get': {
                'protector': user_protector,
                'handler': pass_view.create_barcode,
                'in_dto': None,
                'out_dto': None,
            },
        },
    },
}
auth_endpoints = {
    '/auth': {
        'v1': {
            'post': {
                'handler': auth_view.user_auth_handler,
                'in_dto': service_dto.Auth.LoginDto,
                'response_fabric': auth_response_fabric,
                'out_dto': response_dto.AuthResponse,
            },
        },
    },
}
routes_dict = {
    "apps": [
        {
            "app_name": "asbp",
            "version_prefix": "/api/v",
            "endpoints": {}
        }
    ]
}

routes_dict['apps'][0]['endpoints'].update(access_endpoints)

for app_route in routes_dict.get("apps"):
    version_prefix = app_route.get("version_prefix")
    version_prefix = version_prefix if version_prefix else "/api/v"
    secured_handlers = []
    for endpoint, versions in app_route.get("endpoints").items():
        for version, params in versions.items():
            methods_confs = []
            endpoint_handler = params.get("handler", None)
            endpoint_protector = params.get("protector", None)
            for method_name, method_params in params.items():
                if not isinstance(method_params, dict):
                    continue
                target_func = method_params.get('handler')
                target_func = target_func if target_func else endpoint_handler
                protector = method_params.get("protector")
                protector = protector if protector else endpoint_protector
                if protector in [user_protector]:
                    if target_func not in secured_handlers:
                        sanic_ext.openapi.parameter(
                            name=f"session", schema=int, location="cookie", required=True)(target_func)
                        secured_handlers.append(target_func)
                    if protector == user_protector:
                        sanic_ext.openapi.secured({"cookieAuth": ["user"]})(target_func)
