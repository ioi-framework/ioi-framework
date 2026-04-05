#!/usr/bin/env python3
"""
Generate Office XML-only JSON-LD for AF-012.

This mapper intentionally keeps Office metadata separate from MFT evidence so
AF-012 can load and query independent Office and MFT graphs.
"""

from __future__ import annotations

import json
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_xml_core(xml_path: Path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {
            "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
        }
        creator = root.find(".//dc:creator", ns)
        last_modified_by = root.find(".//cp:lastModifiedBy", ns)
        dcterms_created = root.find(".//dcterms:created", ns)
        dcterms_modified = root.find(".//dcterms:modified", ns)
        return {
            "dc_creator": creator.text if creator is not None else "",
            "last_modified_by": last_modified_by.text if last_modified_by is not None else "",
            "dcterms_created": dcterms_created.text if dcterms_created is not None else "",
            "dcterms_modified": dcterms_modified.text if dcterms_modified is not None else "",
        }
    except Exception as exc:
        print(f"Error parsing XML {xml_path}: {exc}")
        return None


def office_docs_from_folder(xml_folder_path: Path):
    docs = []
    for doc_folder in sorted(xml_folder_path.iterdir()):
        if not doc_folder.is_dir():
            continue
        core_xml = doc_folder / "docProps" / "core.xml"
        if not core_xml.exists():
            continue
        doc_name = doc_folder.name.replace("(xml)", "").strip()
        xml_data = parse_xml_core(core_xml)
        if not xml_data:
            continue
        docs.append((doc_name, doc_folder, xml_data))
    return docs


def build_document_node(doc_name: str, doc_folder: Path, xml_data: dict):
    entry_uuid = str(uuid.uuid4())
    return {
        "@id": f"kb:office-doc--{entry_uuid}",
        "@type": "observable:File",
        "core:hasFacet": [
            {
                "@id": f"kb:file-facet--{entry_uuid}",
                "@type": ["core:Facet", "observable:FileFacet"],
                "observable:fileName": doc_name,
                "observable:filePath": doc_name,
                "observable:extension": Path(doc_name).suffix,
                "observable:isDirectory": False,
            },
            {
                "@id": f"kb:content-facet--{entry_uuid}",
                "@type": ["core:Facet", "observable:ContentDataFacet"],
                "observable:creator": xml_data["dc_creator"],
            },
            {
                "@id": f"kb:xml-metadata-facet--{entry_uuid}",
                "@type": ["core:Facet", "ioi-ext:OfficeXmlMetadataFacet"],
                "ioi-ext:dctermsCreated": {
                    "@type": "xsd:dateTime",
                    "@value": xml_data["dcterms_created"],
                },
                "ioi-ext:dctermsModified": {
                    "@type": "xsd:dateTime",
                    "@value": xml_data["dcterms_modified"],
                },
                "ioi-ext:lastModifiedBy": xml_data["last_modified_by"],
                "ioi-ext:metadataSource": str((doc_folder / "docProps" / "core.xml").relative_to(doc_folder.parent)),
            },
        ],
    }


def build_graph(xml_folder_path: Path):
    nodes = []
    for doc_name, doc_folder, xml_data in office_docs_from_folder(xml_folder_path):
        nodes.append(build_document_node(doc_name, doc_folder, xml_data))
    return {
        "@context": {
            "core": "https://ontology.unifiedcyberontology.org/uco/core/",
            "observable": "https://ontology.unifiedcyberontology.org/uco/observable/",
            "uco-action": "https://ontology.unifiedcyberontology.org/uco/action/",
            "investigation": "https://ontology.caseontology.org/case/investigation/",
            "ioi-ext": "https://ioi-framework.github.io/ns/ioi-ext/",
            "kb": "http://example.org/kb/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "core:hasFacet": {"@type": "@id"},
            "core:object": {"@type": "@id"},
            "uco-action:object": {"@type": "@id"},
        },
        "@graph": nodes,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python office_xml_only_filler.py <xml_folder> <output.jsonld>")
        sys.exit(1)

    xml_folder = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    graph = build_graph(xml_folder)
    output_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Generated: {output_path}")
    print(f"   - Office documents: {len(graph['@graph'])}")


if __name__ == "__main__":
    main()
