# coding=utf-8
import logging

from flask import Blueprint
from flask import make_response
from flask_restplus import Api

from mycodo.mycodo_flask.api.choices import ns_choices_measurement
from mycodo.mycodo_flask.api.controller import ns_controller
from mycodo.mycodo_flask.api.daemon import ns_daemon
from mycodo.mycodo_flask.api.measurement import ns_measurement
from mycodo.mycodo_flask.api.output import ns_output
from mycodo.mycodo_flask.api.settings import ns_settings

logger = logging.getLogger(__name__)

api_blueprint = Blueprint('api', __name__, url_prefix='/api')

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api = Api(
    api_blueprint,
    version='1.0',
    title='Mycodo API',
    description='An API for Mycodo',
    authorizations=authorizations,
    default_mediatype='application/vnd.mycodo.v1+json'
)

api.add_namespace(ns_choices_measurement)
api.add_namespace(ns_controller)
api.add_namespace(ns_daemon)
api.add_namespace(ns_measurement)
api.add_namespace(ns_output)
api.add_namespace(ns_settings)

# Remove default accept header content type
if 'application/json' in api.representations:
    del api.representations['application/json']

# Add API v1 + json accept content type
@api.representation('application/vnd.mycodo.v1+json')
def api_v1(data, code, headers):
    resp = make_response(data, code)
    resp.headers.extend(headers)
    return resp

# To be used when v2 of the API is released
# @api.representation('application/vnd.mycodo.v2+json')
# def api_v2(data, code, headers):
#     resp = make_response(data, code)
#     resp.headers.extend(headers)
#     return resp
