import json
import os

from this_compute.validators import validate_datacite_json


fixtures_dir = os.path.join(
    os.path.dirname(__file__),
    'fixtures'
)


def test_valid_schema():
    fn = os.path.join(fixtures_dir, 'example_metadata_good.json')
    with open(fn) as f:
        content = json.load(f)

    res = validate_datacite_json(content)
    assert len(res) == 0, "No validation errors expected"


def test_invalid_schema():
    fn = os.path.join(fixtures_dir, 'example_metadata_bad.json')
    with open(fn) as f:
        content = json.load(f)

    res = validate_datacite_json(content)
    assert len(res) == 2, "Two validation errors expected"

    bad_fields = sorted(e['field'] for e in res)
    expected = ["$.creators[0]", "$.titles[0].title"]
    assert bad_fields == expected, "Unexpected bad fields"
