"""
Validate a set of input according to a (modified) DataCite 4.6 JSON-format schema

Base schema docs:
    https://datacite-metadata-schema.readthedocs.io/_/downloads/en/4.6/pdf/
    https://support.datacite.org/docs/datacite-xml-to-json-mapping

Notes on fields left out of this implementation:
    https://app.shortcut.com/globus/story/40680/create-candidate-single-index-schema-for-data-ingest
"""
import typing as t
from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator


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


class JVErr(t.TypedDict):
    message: str
    field: str


def validate_datacite_json(metadata_content: dict) -> list[JVErr]:
    """Return all validation errors in user-provided document, according to our modified datacite schema"""
    try:
        validator = Draft202012Validator(DC_SCHEMA)
        validator.check_schema(DC_SCHEMA)
    except SchemaError as e:
        raise Exception('Invalid schema was provided to validation function')

    return [ # type: ignore
        {'message': e.message, 'field': e.json_path} # type: ignore
        for e in validator.iter_errors(metadata_content)
    ]

