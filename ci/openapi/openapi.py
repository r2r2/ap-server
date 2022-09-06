import inspect
import json as main_json
import re
from typing import Dict

from sanic import Request
from sanic.response import json
from sanic_openapi import openapi3_blueprint, specification

from core.server.controllers import BaseAccessController
from core.server.routes import BaseServiceController
from settings import BASE_DIR


class SanicRoutesFormatter:

    SANIC_ROUTES_FILEPATH = f"{BASE_DIR}/ci/openapi/sanic_routes.json"
    SYSTEM_PATHS_TAG = 'SYSTEM'
    SECURITY_SCHEME_NAME = 'CookiesAuth'
    not_required_scheme_names = ['CallViaNumberDto']

    def __init__(self, sanic_app):
        self.sanic_app = sanic_app

    def get_routes(self) -> Dict:
        access_routes = {}
        for access_controller in BaseAccessController.__subclasses__():
            access_routes[access_controller.entity_name] = access_controller.enabled_scopes

        service_routes = {}
        for service_controller in BaseServiceController.__subclasses__():
            if "<entity:int>" not in service_controller.target_route:
                service_routes[service_controller.target_route[1:]] = service_controller.enabled_scopes

        all_routes = {}
        for name, route in self.sanic_app.router.routes_all.items():
            if not hasattr(route.handler, "view_class"):
                continue
            if hasattr(route.handler.view_class, "enabled_scopes"):
                scopes = route.handler.view_class.enabled_scopes
            else:
                scopes = []

            # ----- set service name ---------- #
            if hasattr(route.handler.view_class, "target_service"):
                service = route.handler.view_class.target_service.__name__
            elif hasattr(route.handler.view_class, "access_type"):
                service = route.handler.view_class.access_type.__name__
            else:
                service = self.SYSTEM_PATHS_TAG

            # -------- get DTO schemas --------- #
            creation_dto = None
            if hasattr(route.handler.view_class, "post_dto") and getattr(route.handler.view_class, "post_dto"):
                creation_dto = route.handler.view_class.post_dto.schema(ref_template="#/components/schemas/{model}")

            update_dto = None
            if hasattr(route.handler.view_class, "put_dto") and getattr(route.handler.view_class, "put_dto"):
                update_dto = route.handler.view_class.put_dto.schema(ref_template="#/components/schemas/{model}")

            # ------- correct route and methods --------- #
            both_routes = {**access_routes, **service_routes}
            methods: list = list(route.methods)
            path: str = f"/{route.path}"

            if route.path in both_routes:
                methods.remove("DELETE")
                methods.remove("PUT")

            elif "<entity:int>" in route.path:
                methods.remove("POST")
                npath = path.replace("/<entity:int>", "")
                entity_name = npath.split("/")[-1]
                path = path.replace("entity", f"{entity_name}_id")

            # ----------- get query args ------- #
            query_args = {}
            for method in methods:
                func = getattr(route.handler.view_class, method.lower())
                func_text = inspect.getsource(func)
                func_query_args = re.findall(r"request.args.get\(\"(\w*)\"\)", func_text)
                if func_query_args:
                    query_args = {method.lower(): func_query_args}

            # ---------- append to result ------- #
            route_dict = {"path": path, "methods": methods, "scopes": scopes,
                          "creation_dto": creation_dto, "update_dto": update_dto,
                          "query_args": query_args}
            if all_routes.get(service):
                all_routes[service].append(route_dict)
            else:
                all_routes[service] = [route_dict]

        return all_routes

    def get_routes_with_body(self, all_routes):
        def add_request_body(method: str, schema: dict, path: str, paths: dict, components: dict):
            if not schema:
                return
            if "definitions" in schema:
                if components.get("schemas"):
                    components["schemas"].update(schema.pop("definitions"))
                else:
                    components["schemas"] = schema.pop("definitions")
            if not paths[path].get(method):
                paths[path][method] = {}
            paths[path][method]["requestBody"] = {
                "content": {
                    "application/json": {"schema": schema}
                },
                "required": True if schema['title'] not in self.not_required_scheme_names else False
            }

        paths = {}
        components = {}
        tags = []
        for key in all_routes:
            tags.append(key)
            for route in sorted(all_routes[key], key=lambda rr: rr['path']):
                paths[route['path']] = {}
                # ----- add request body to post and put methods ------ #
                for method_name in route['methods']:
                    method_name = method_name.lower()
                    if not paths[route['path']].get(method_name):
                        paths[route['path']][method_name] = {}
                    if "post" == method_name:
                        add_request_body("post", route['creation_dto'], route['path'], paths, components)
                    if "put" == method_name:
                        add_request_body("put", route['update_dto'], route['path'], paths, components)

                # ----- add query params and security -------- #
                for method in paths[route['path']]:

                    if "_id" in route['path']:
                        route['query_args']['get'] = []

                    paths[route['path']][method]["tags"] = [key]
                    if route["query_args"] and route["query_args"].get(method):
                        if not paths[route['path']][method].get("parameters"):
                            paths[route['path']][method]["parameters"] = []
                        for param in route["query_args"][method]:
                            paths[route['path']][method]["parameters"].append({'name': param,
                                                                               'required': False,
                                                                               'in': 'query',
                                                                               'schema': {'type': 'string'}})

                    if route['scopes']:
                        paths[route['path']][method]['security'] = {self.SECURITY_SCHEME_NAME: []}
                    if self.SYSTEM_PATHS_TAG == key and "auth" in route['path']:
                        paths[route['path']][method]["responses"] = {
                            "default": {
                                "description": "OK",
                                "headers": {
                                    "Set-Cookie": {
                                        "description": "Session cookie", "schema": {"type": "string"}},
                                    "\0Set-Cookie": {
                                        "description": "Token cookie", "schema": {"type": "string"}},
                                    "\0\0Set-Cookie": {
                                        "description": "Expire_at cookie", "schema": {"type": "string"}},
                                }
                            }
                        }

        components["securitySchemes"] = {self.SECURITY_SCHEME_NAME: {"type": "token", "in": "cookie"}}

        return {"paths": paths, "components": components, 'tags': tags}

    @staticmethod
    def format_swagger_paths(swagger_paths):
        def add_path_params(_path, _methods):
            _path_params = re.findall(r"{(\w*)}", _path)
            if not _path_params:
                return
            for _method in _methods.values():
                for _param in _path_params:
                    if _param not in [p['name'] for p in _method["parameters"]] and "id" in _param:
                        _method["parameters"].append({'name': _param, 'schema': {'type': 'integer', 'format': 'int32'},
                                                      'required': True, 'in': 'path'})

        def remove_unused_path_params(_path, _methods):
            _path_params = re.findall(r"{(\w*)}", _path)
            for _method in _methods.values():
                for _param in _method["parameters"].copy():
                    if _param['name'] not in _path_params:
                        _method["parameters"].remove(_param)

        nswpaths = {}
        for swpath, methods in swagger_paths.items():
            path_params = re.findall(r"{(\w*)}", swpath)

            if "entity" in path_params:
                npath = swpath.replace("/{entity}", "")
                entity_name = npath.split("/")[-1]
                param_name = f"{entity_name}_id"
                path = swpath.replace("entity", param_name)

                methods.pop("post", None)

                for method in methods.values():
                    for param in method["parameters"]:
                        if param['name'] == 'entity':
                            param['name'] = param_name
                            param['required'] = False

            else:
                path = swpath
                [methods.pop(key, None) for key in ['delete', 'put']]

            add_path_params(path, methods)
            remove_unused_path_params(path, methods)
            nswpaths[path] = methods
        return nswpaths

    @staticmethod
    def format_sanic_paths(sanic_paths):
        """format path params from <someparam:type> to {someparam}"""
        new_paths = {}
        for path, methods in sanic_paths.items():
            for res in re.findall(r"(<(\w*):\w*>)", path):
                path = path.replace(res[0], f"{{{res[1]}}}")
            new_paths[path] = methods
        return new_paths

    def create_sanic_js(self):
        routes = self.get_routes()
        sanic_js = self.get_routes_with_body(routes)
        sanic_js['paths'] = self.format_sanic_paths(sanic_js['paths'])

        with open(self.SANIC_ROUTES_FILEPATH, "w") as f:
            main_json.dump(sanic_js, f)

    @staticmethod
    def combine_paths(sanic_js, swagger_js):

        for path, methods in swagger_js['paths'].items():
            if path not in sanic_js["paths"]:
                continue
            tags = []
            for smethod in sanic_js["paths"][path]:
                if 'tags' in sanic_js["paths"][path][smethod]:
                    for tag in sanic_js["paths"][path][smethod]['tags']:
                        if tag not in tags:
                            tags.append(tag)

            for method in methods:
                methods[method]['tags'] = tags
                if method in sanic_js["paths"][path]:
                    methods[method].update(sanic_js["paths"][path][method])

        if not swagger_js.get('components'):
            swagger_js['components'] = sanic_js['components']
        else:
            swagger_js['components'].update(sanic_js['components'])
        if not swagger_js.get('tags'):
            swagger_js['tags'] = sanic_js['tags']
        else:
            swagger_js['tags'].extend(sanic_js['tags'])
        return swagger_js


def overwrite_swagger_route(openapi_blueprint):
    """overwrite "/swagger.json" route"""

    for route in openapi_blueprint._future_routes:
        if route.uri == '/swagger.json':
            openapi_blueprint._future_routes.remove(route)
            break

    @openapi_blueprint.route("/swagger.json")
    def spec(request: Request):
        sanic_js = main_json.load(open(SanicRoutesFormatter.SANIC_ROUTES_FILEPATH))
        swagger_js = specification.build().serialize()
        swagger_js['paths'] = SanicRoutesFormatter.format_swagger_paths(swagger_js['paths'])

        return json(SanicRoutesFormatter.combine_paths(sanic_js, swagger_js))


if __name__ == '__main__':
    from cli import App

    app = App()

    op3 = openapi3_blueprint
    op3.name = "swagger"
    overwrite_swagger_route(op3)
    app.server.sanic_app.blueprint(op3)

    SanicRoutesFormatter(app.server.sanic_app).create_sanic_js()  # save routes to file, because of pydantic

    app.server.sanic_app.config.API_TITLE = "ASBP API"
    app.run()
