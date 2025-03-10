#!/usr/bin/env python3
"""
Parse an RIS format file into records usable in a Globus search index

Demonstrates data cleanup, then adds a few specialized and silly things to support one specific demo

"""
import argparse
from datetime import datetime, timezone
import json
import random
import urllib.parse

import rispy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    # This demo dataset lists local paths, which we assume are all in the same endpoint folder. In the future we can programmatically retrieve URLs from collection ID, via the SDK
    # The "file transfer" feature uses relative paths, but embeds use absolute paths. This hardcodes the globus URL of a specific guest collection, as determined via app.globus.org. Our script will construct full URL to the asset for now.
    # In initial demo, sample file field needs a little help to be used as a webapp embed. Can webapp be smarter?
    parser.add_argument('--base-url', help="The HTTPS URL for this Globus endpoint (see app.globus.org to get yours)", required=True)
    parser.add_argument('--group-id', help="The uuid of a private globus group. Used to demonstrate permissions, for any file tagged `hidden``")  # Optional. If omitted, principal sets queries won't work for this demo.
    return parser.parse_args()


def ris_to_date(date_spec: str) -> datetime.date:
    """
    The zotero RIS date exporter is a bit silly: Whatever YMD fields given, plus a bunch of extra slashes.
    
    Convert these into timestamps that ES can index, so we aren't left with weird dates like `2014//`
    """
    parts = [
        p 
        for p in date_spec.split('/')
        if p != ''  # Y+M is rendered as Y/M/ (empty string for day)
    ]
    if len(parts) == 0:
        return None

    y = int(parts[0])
    # Some dates may omit m/d, like "journal pub" or "conf". Set default = 1 if not provided, eg 2014 -> Jan 1, 2014
    m = int(parts[1]) if len(parts) > 1 else 1
    d = int(parts[2]) if len(parts) > 2 else 1
    ts = datetime(y, m, d, tzinfo=timezone.utc)
    # Elasticsearch will parse iso formatted strings as dates
    return ts.isoformat()


def cleanup_citation(base_url, ris_record: dict):
    """Clean up entries by removing RIS format keys that are messy or useless; prepare entries for indexing"""
    REMOVE_KEYS = {'access_date', 'language', 'database_provider', 'language', 'unknown_tag'}

    tidy = {}
    files = []
    for k, v in ris_record.items():
        if k in REMOVE_KEYS:
            continue
        elif (k.startswith('file_attachments') or k.startswith('figure')):
            # Remove the many separate file fields from the record, and replace with one list of allowed filetypes
            # Exclude PDF and HTML, because in my dataset, those are copyrighted articles that we can't redistribute
            if not (v.endswith('.pdf') or v.endswith('.html')):
                files.append(v)
        else:
            tidy[k] = v

    # RIS format happens to have a provision for files, so "supporting assets" were already in a handy format/location. Some citation formats would need more review/handling.
    # The search index just stores a string matching pathname. It's your job to transfer those files to a globus endpoint, and keep the search index and filesystem in sync!
    tidy['files'] = files

    if sf:= (files[0] if len(files) > 0 else None):
        # Right now the embed viewer only handles exactly one item per field (not array), and doesn't fetch type directly. For the demo, we have a few hacks:
        if 'plotly' in sf:
            # Plotly plots require a specifically transformed json file of data + plot options, prepared in advance. We'll assume the files are named with a convention that provides plots for this demo of embed functionality.
            tidy['sample_plot_url'] = urllib.parse.urljoin(base_url, sf)

        # Also insert same file as generic sample. This is because the demo website sort of glitches without something in this field.
        tidy['sample_file'] = sf
        tidy['sample_file_url'] = urllib.parse.urljoin(base_url, sf)

    d = tidy.get('date', tidy.get('year'))
    if d is not None:
        # Fix dates, allowing more than one source field as fallback (books and conferences sometimes only report year)
        tidy['date'] = ris_to_date(d)

    return tidy


def make_pathogens():
    """
    Annotate each article with one or more pathogens. This is mock (fake) data, and we will use it to demonstrate faceted search.
    """
    # Scrape "pathogen or disease" list from:
    #    https://violinet.org/vaximmutordb/index.php
    pathogens = ["Any pathogen","Actinobacillus pleuropneumoniae","Aeromonas hydrophila","Arthritis","Bacillus anthracis","Bordetella bronchiseptica","Brucella spp.","Burkholderia pseudomallei","Campylobacter jejuni","Canine parvovirus","Chlamydia muridarum","Chlamydophila abortus","Chlamydophila pneumoniae","Coxiella burnetii","Cryptosporidium parvum","Edwardsiella ictaluri","Eimeria maxima","Escherichia coli","Francisella tularensis","Haemophilus influenzae","Hantavirus","Herpes simplex virus type 1 and 2","Human Immunodeficiency Virus","Influenza virus","Japanese encephalitis virus","Leishmania donovani","Leishmania infantum","Listeria monocytogenes","Measles virus","Mycobacterium avium","Mycobacterium tuberculosis","Mycoplasma gallisepticum","Pasteurella multocida","Porcine circovirus 2","Pseudorabies virus","Rickettsia spp","Rotavirus","Salmonella spp.","Shigella","Staphylococcus aureus","Streptococcus equi","Streptococcus pyogenes","Toxoplasma gondii","Vaccinia virus","Vibrio cholerae","West Nile virus","Yellow fever virus","Yersinia enterocolitica","Yersinia pestis"]
    return random.sample(pathogens, random.randint(1,2))


def build_record(citation: dict):
    """Fill in the data fields for a record: citation + other supporting information"""
    if 'id' not in citation:
        citation['id'] = citation.get(
            'doi',  # Most things have a DOI.
            # TODO: Find a better default ID- titles may not always be distinct enough, and uuids are randomized,
            #   which would make the subject ID change on every re-ingest... this is a demo script shortcut
            '{}_{}'.format(citation.get('title'), citation.get('date'))
        )

    # Move certain fields above the citation, because they may power other webapp features
    keywords = citation.pop('keywords', None)
    files = citation.pop('files', None)
    sample_file = citation.pop('sample_file', "")  ## Static search portal UI prefers empty strings instead of null
    sample_file_url = citation.pop('sample_file_url', "")
    sample_plot_url = citation.pop('sample_plot_url', "")

    return {
        'citation': citation,
        'bio_annotations': make_pathogens(),  # Synthetic data!
        'files': files,
        'sample_file': sample_file,
        'sample_file_url': sample_file_url,
        'sample_plot_url': sample_plot_url,  # Currently, the static apps aren't smart enough to auto-detect whether a file should be rendered as a plot or not. Separate field allows us to hard-code different behavior by field name.
        'keywords': keywords,
    }


def citation_to_gingest(record: dict, admin_group_urn=''):
    """
    Add options and format specific to Globus, including permissions

    This is a dummy script, so it can make some special assumptions. Permissions are controlled by the magic
     tag/keyword "hidden"` in my personal sample dataset (if present, extra restrictions are applied):
    """
    is_hidden = ('hidden' in record.get('keywords', []))

    # In practice, principal sets are defined on every single record, but the content is always the same. Updating members of a principal set would require re-indexing every single record!
    #  To avoid maintenance burden when set members change, we strongly encourage the use of Globus Groups as principals, and making all member changes to the group (not the search record)
    secret_principal = {'curators': [admin_group_urn]}  # these principal groups can be called any name you want; I chose a word not used by other globus features for clarity

    record = {
        "id": "pub_record",
        "subject": record['citation']['id'],
        "visible_to": ['all_authenticated_users' if is_hidden else 'public'],
        "content": record
    }

    if is_hidden and admin_group_urn:
        record['principal_sets'] = secret_principal

    return record


def to_gingest_payload(records: list[dict]) -> dict:
    """Make the final combined document that will be submitted directly to the globus search API"""
    return {
        "ingest_type": "GMetaList",
        "ingest_data": {
            "gmeta": records
        }
    }
    
    

if __name__ == '__main__':
    args = parse_args()
    globus_admin_group_urn = f'urn:globus:groups:id:{args.group_id or ""}'

    with open(args.input, 'r') as f:
        ris_entries = rispy.load(f)  # type: list[dict]

    records = []
    for r in ris_entries:
        # Build record data, then add globus search permissions rules
        t = cleanup_citation(args.base_url, r)
        t = build_record(t)
        t = citation_to_gingest(t, admin_group_urn=globus_admin_group_urn)
        records.append(t)

    # Add wrapper for globus ingest payload
    res = to_gingest_payload(records)

    out_fn= args.output

    with open(args.output, 'w') as f:
        json.dump(res, f, indent=2)

    print(f'Wrote {len(records)} records to {out_fn}')
