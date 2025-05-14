"""
Test out bits of logic locally:

* Download a file via HTTPS
* Validate against a jsonschema and report errors to the flow if necessary
"""
def compute_wrapper(collection_id: str, metadata_fn: str):
    """
    All Globus compute functions must be serialized within a single parent function
    This one expects GLOBUS_CLIENT_ID and GLOBUS_CLIENT_SECRET to be set as worker envvars,
    and the function will be called with the path to the file we want to read
    """
    import logging
    import os
    from urllib.parse import urljoin

    from globus_sdk import TransferClient, ClientApp
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


    def create_app(client_id, client_secret, collection_id):
        """
        Generate a client app that can log in using credentials from envvars. This client must have identity access to the specified collection.
        """
        return ClientApp(
            client_id=client_id,
            client_secret=client_secret,
            scope_requirements={
                'auth.globus.org': ['openid', 'profile', 'email'],
                collection_id: [f'https://auth.globus.org/scopes/{collection_id}/https']
            }
        )


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


    def get_https_request_headers(app: ClientApp, collection_id: str) -> dict:
        t = app.token_storage.get_token_data(collection_id)
        return {'Authorization': f'Bearer {t.access_token}'}


    def get_file_content(collection_base_url: str, filename: str, auth_headers: dict) -> dict:
        url = urljoin(collection_base_url, filename)

        logger.info(f'Requesting file at {url}')

        headers = {
            **auth_headers,
            # Ensure errors are represented as machine-readable JSON
            "X-Requested-With": "XMLHttpRequest",
        }
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            raise Exception(f"Failed to retrieve file with code {res.status_code}")

        try:
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f'Request for URL {url} failed with code {res.status_code}')
            logger.warning(res.text)
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


    def main(client_id, client_secret, collection_id, filename):
        """The real body of the function that assembles all the steps"""
        app = create_app(client_id, client_secret, collection_id)
        client = TransferClient(app=app)

        app.login()

        if requires_data_access_scope(client, collection_id):
            raise NotImplementedError('Only non-HA guest collections are supported.')

        collection_https_url = get_https_url(client, collection_id)
        headers = get_https_request_headers(app, collection_id)

        content = get_file_content(collection_https_url, filename, headers)
        val = validate_result(content)

        if len(val) > 0:
            logger.error('Invalid user input!')
            logger.error(val)
        return val

    ##### As far as GCS is concerned, here is the main body of the function
    client_id = os.environ['GLOBUS_CLIENT_ID']
    client_secret = os.environ['GLOBUS_CLIENT_SECRET']
    return main(client_id, client_secret, collection_id, metadata_fn)


if __name__ == '__main__':
    # Just for local testing purposes. Demonstrates how it would be called in GCS.
    COLLECTION_ID = "dba0d7c0-1f63-44d1-bcd0-76865d3d44a0"  # GUEST-ified personal collection
    # res = compute_wrapper(COLLECTION_ID, '/subfolder/metadata.json') # A good file in my specific collection
    res = compute_wrapper(COLLECTION_ID, '/subfolder/example_metadata_bad.json')
    print('Script has completed. Result: {}'.format(res))
