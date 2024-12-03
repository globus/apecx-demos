"""
Parse an RIS format file into records usable in a Globus search index

Demonstrates data cleanup, then adds a few specialized and silly things to support one specific demo
"""
import urllib.parse
from datetime import datetime, timezone
import json
import random

import rispy

def ris_to_date(date_spec: str) -> datetime.date:
    """
    RIS dates are a bit silly: Whatever YMD fields given, plus a bunch of extra slashes.
    
    Convert these into timestamps that ES can index
    """
    parts = [
        p 
        for p in date_spec.split('/')
        if p != ''  # Y+M is rendered as Y/M/ (empty string for day)
    ]
    if len(parts) == 0:
        return None

    y = int(parts[0])
    # Some dates may omit m/d, like "journal pub" or "conf". Set default = 1 if not provided
    m = int(parts[1]) if len(parts) > 1 else 1
    d = int(parts[2]) if len(parts) > 2 else 1
    ts = datetime(y, m, d, tzinfo=timezone.utc)

    return ts.isoformat()


def cleanup_citation(base_url, ris_record: dict):
    # Clean up entries by removing RIS format keys that are messy or useless; prepare entries for indexing
    REMOVE_KEYS = {'access_date', 'language', 'database_provider', 'language', 'unknown_tag'}

    tidy = {}
    files = []
    for k, v in ris_record.items():
        if k in REMOVE_KEYS:
            continue
        elif (k.startswith('file_attachments') or k.startswith('figure')):
            # Remove the many separate file fields from the record, and replace with one list of allowed filetypes
            # Exclude PDF and HTML, because in my dataset, those are copyrighted articles we don't want to share
            if not (v.endswith('.pdf') or v.endswith('.html')):
                files.append(v)
        else:
            tidy[k] = v

    # RIS format happens to have a provision for files, so "supporting assets" were already in a handy format/location. Some citation formats would need more review/handling.
    tidy['files'] = files

    if sf:= (files[0] if len(files) > 0 else None):
        # Right now the embed viewer only handles exactly one item per field (not array), and doesn't fetch type directly. For the demo, we have a few hacks:
        if 'plotly' in sf:
            # Plotly plots require a specifically transformed json file of data + plot options, prepared in advance. We'll assume the files are named with a convention that provides plots for this demo of embed functionality.
            tidy['sample_plot_url'] = urllib.parse.urljoin(base_url, sf)

        # Also insert same file as generic sample. This is because the demo sort of glitches without something in this field.
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
    """Citation data """
    if 'id' not in citation:
        citation['id'] = citation.get(
            'doi',  # Most things have a DOI.
            # TODO: Find a better default ID- titles may not always be distinct enough, and uuids aren't stable enough... but this is a demo script
            '{}_{}'.format(citation.get('title'), citation.get('date'))
        )

    # Move certain fields above the citation, because they may be integrated separately
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
        'sample_plot_url': sample_plot_url,
        'keywords': keywords,
    }



def citations_to_gingest(records: list[dict]) -> dict:
    """Make the final combined document that will be submitted directly to the globus search API"""
    return {
        "ingest_type": "GMetaList",
        "ingest_data": {
            "gmeta": [
                {
                    "id": "pub_record",
                    "subject": r['citation']['id'],
                    "visible_to": ['public'],
                    "content": r
                }
                for i, r in enumerate(records)
            ]
        }
    }
    
    

if __name__ == '__main__':
    path = '/Users/abought/Desktop/search-demo-data/abought-papers/abought-papers.ris'

    # The "file transfer" feature uses relative paths, but embeds use absolute paths. This hardcodes the globus URL of a specific guest collection, as determined via app.globus.org. Our script will construct full URL to the asset for now.
    #
    # In initial demo, sample file field needs a little help to be used as a webapp embed. Can webapp be smarter?
    GLOBUS_BASE_URL = "https://g-a68a94.554f69.8540.data.globus.org"

    with open(path, 'r') as f:
        ris_entries = rispy.load(f)  # type: list[dict]

    records = []
    for r in ris_entries:
        t = cleanup_citation(GLOBUS_BASE_URL, r)
        t = build_record(t)

        records.append(t)

    res = citations_to_gingest(records)



    outpath = '../data/abought-citations-as-globus-gingest.json'
    with open(outpath, 'w') as f:
        json.dump(res, f, indent=2)

    print(outpath)