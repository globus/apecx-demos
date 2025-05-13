"""
Test out bits of logic locally:

* Download a file via HTTPS
* Validate against a jsonschema and report errors to the flow if necessary


TODO When productionizing: How are compute function errors returned to a flow?
"""
import logging
import json
from urllib.parse import urljoin

from globus_sdk import TransferClient, UserApp
import requests
from jsonschema import ValidationError
from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator

logger = logging.getLogger(__name__)

DC_SCHEMA = {
    "type": "object",
    "title": "Search metadata",
    "description": "Metadata that will be used to populate a search index. Simplified from datacite 4.6; in future we will add custom extra fields.",
    "properties": {
        "identifier": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string"
                },
                "identifierType": {
                    "type": "string"
                }
            },
            "required": [
                "identifier"
            ]
        },
        "creators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "nameType": {
                        "type": "string",
                        "enum": [
                            "Organizational",
                            "Personal"
                        ]
                    },
                    "givenName": {
                        "type": "string"
                    },
                    "familyName": {
                        "type": "string"
                    },
                    "affiliation": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "name"
                        ]
                    }
                },
                "required": [
                    "name"
                ]
            }
        },
        "titles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string"
                    },
                    "titleType": {
                        "type": "string"
                    }
                },
                "required": [
                    "title"
                ]
            }
        },
        "publisher": {
            "type": "object",
            "description": "The name of the institution that produced the resource",
            "properties": {
                "name": {
                    "type": "string"
                }
            },
            "required": ["name"]
        },
        "publicationYear": {
            "type": "integer"
        },
        "resourceType": {
            "type": "object",
            "properties": {
                "resourceType": {
                    "type": "string"
                },
                "resourceTypeGeneral": {
                    "type": "string"
                }
            },
            "required": [
                "resourceTypeGeneral"
            ]
        },
        "dates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "dateType": {
                        "type": "string",
                        "enum": ["Created", "Submitted", "Updated"]
                    }
                },
                "required": [
                    "date",
                    "dateType"
                ]
            }
        },
        "alternateIdentifiers": {
            "type": "array",
            "description": "Other ways that the resource may be recognized. For example, PDB, uniprot ID, DOI...",
            "items": {
                "type": "object",
                "properties": {
                    "alternateIdentifier": {
                        "type": "string"
                    },
                    "alternateIdentifierType": {
                        "type": "string"
                    }
                }
            }
        },
        "formats": {
            "type": "array",
            "description": "(optional) The Technical format of the resource, such as mimetype/file format. Used to guide searches for data compatible with analysis software",
            "items": {
                "type": "string"
            }
        },
        "version": {
            "type": "string"
        },
        "rightsList": {
            "type": "array",
            "description": "Information about licensing and reuse rules (such as CC-BY-4.0)",
            "items": {
                "type": "object",
                "properties": {
                    "rights": {
                        "description": "Text description of the license or access restriction",
                        "type": "string"
                    },
                    "rightsURI": {
                        "type": "string",
                        "description": "A url containing details of the license or access restrictions (optional)"
                    },
                    "rightsIdentifier": {
                        "description": "A unique ID for the license, such as from https://spdx.org/licenses/",
                        "type": "string"
                    }
                },
                "required": ["rights"]
            }
        },
        "descriptions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string"
                    },
                    "descriptionType": {
                        "type": "string"
                    }
                },
                "required": [
                    "description"
                ]
            }
        }
    },
    "required": [
        "identifier",
        "creators",
        "titles",
        "publisher",
        "publicationYear"
    ],
    "additionalProperties": False
}

def create_client(client_id: str):
    # TODO: Determine how client sdk credentials might be consumed in a globus compute function within a flow
    app = UserApp(client_id=client_id)
    return TransferClient(app=app)


def requires_data_access_scope(client: TransferClient, coll_id: str) -> bool:
    """
    Standard error checking safeguard: ensures that the target collection is guest (not mapped) and
    """
    r = client.get_endpoint(coll_id)
    if not r.http_status == 200:
        logger.debug(f"Guest collection endpoint returned status {r.http_status} - {r.http_reason}")
        logger.debug(r)
        raise Exception(f"Error encountered while querying status for endpoint {coll_id}")
    return (r.data['high_assurance'] is False) and (r.data['entity_type'] == 'GCSv5_mapped_collection')


def get_https_url(client: TransferClient, coll_id: str) -> str:
    # FIXME: Consider doing this outside the flow, such as via another action
    #    https://docs.globus.org/api/transfer/action-providers/collection-info/
    ep_info = client.get_endpoint(coll_id)
    if not ep_info.http_status == 200:
        raise Exception('Failed to query endpoint')

    if ep_info['high_assurance']:
        logger.warning(
            'High assurance collections may impose special authentication restrictions or timeouts. Consider using a different collection.')
    req_da_scope = (ep_info.data['high_assurance'] is False) and (
                ep_info.data['entity_type'] == 'GCSv5_mapped_collection')
    if req_da_scope or not ep_info['https_server'] or not ep_info['subscription_id']:
        raise NotImplementedError(
            "This collection does not meet requirements. It must be a guest collections, subscribed, with HTTPS access enabled.")

    return ep_info['https_server']







def get_metadata_content(collection_https_url: str, metadata_fn: str = 'metadata.json') -> dict:
    url = urljoin(collection_https_url, metadata_fn)
    res = requests.get(url, headers={"X-Requested-With": "XMLHttpRequest"})
    if res.status_code != 200:
        raise Exception(f"Failed to retrieve file with code {res.status_code}")

    try:
        return res.json()
    except requests.exceptions.RequestException as e:
        print(res.status_code)
        print(res.text)
        raise Exception('Unreadable json response from {}'.format(url))



def validate_result(metadata_content: dict) -> list[dict]:
    """Return all validation errors in user-provided document, according to our modified datacite schema"""
    try:
        validator = Draft202012Validator(DC_SCHEMA)
        validator.check_schema(DC_SCHEMA)
    except SchemaError as e:
        raise Exception('Invalid schema was provided to validation function')
    # NOTE: Compute in a flow will serialize output as json to specified location
    return [
        {'message': e.message, 'field': e.json_path}
        for e in validator.iter_errors(metadata_content)
    ]

if __name__ == '__main__':

    # TODO: This reads files, but only from a guest collection. Need to add permissions logic.
    CLIENT_ID = "5f4fc571-4fa2-4d84-ab6e-567d5245af7a"
    COLLECTION_ID = "dba0d7c0-1f63-44d1-bcd0-76865d3d44a0"


    client = create_client("5f4fc571-4fa2-4d84-ab6e-567d5245af7a")
    requires_data_access_scope(client, COLLECTION_ID)

    base_url = get_https_url(client, COLLECTION_ID)


    # import os
    # base = os.path.dirname(__file__)
    # fn = os.path.abspath(os.path.relpath('../data/example_metadata.json', start=base))
    # with open(fn, 'r') as f:
    #     content = json.load(f)

    content = get_metadata_content(base_url, '/subfolder/example_metadata.json')
    val = validate_result(content)

    if len(val) > 0:
        print('Invalid user input!')
        print(val)
    else:
        print('User input is valid!')



    # TODO: for the HTTPS scope, we'r looking at (rsrc server = collection ID, scope =constructed key with specific collection ID)
    # {
    #   "access_token": "AggM4VmJePzGOBEMEEjwd5GQ6roWDPQG9xDzqxQVnXooap976dCJC6gGY719jj30NeaqWMVPkQyMzqC0Eo6wnTd5rMy",
    #   "scope": "https://auth.globus.org/scopes/06e1f1e9-c778-40ec-beb4-5807af321198/https",
    #   "expires_in": 172800,
    #   "token_type": "Bearer",
    #   "resource_server": "06e1f1e9-c778-40ec-beb4-5807af321198",
    #   "state": "mF3ZcxtvkTqRdTAbqf8y9DVqRgQlrILm"
    # },