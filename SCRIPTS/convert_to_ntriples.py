#!/usr/bin/env python3
"""Convert JSON-LD to N-Triples format.

Primary path: Node.js jsonld package (fast, ~0.3s per file).
Fallback: rdflib (slow for large files, but always available).
"""

import sys
import os
import subprocess
import tempfile


# Inline JS — uses require('jsonld') with NODE_PATH set by caller env
_CONVERT_JS = """\
const jsonld = require('jsonld');
const fs = require('fs');
const inputFile = process.argv[2];
const outputFile = process.argv[3];
try {
    const doc = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
    jsonld.toRDF(doc, {format: 'application/n-quads'}).then(function(nquads) {
        fs.writeFileSync(outputFile, nquads, 'utf8');
        console.log('Done: ' + nquads.length + ' bytes');
        process.exit(0);
    }).catch(function(e) {
        console.error('jsonld error: ' + e.message);
        process.exit(1);
    });
} catch (e) {
    console.error('Parse error: ' + e.message);
    process.exit(1);
}
"""


def _get_npm_global_modules():
    """Return the global node_modules path via `npm root -g`, or None."""
    try:
        r = subprocess.run(
            ['npm', 'root', '-g'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            path = r.stdout.strip()
            if os.path.isdir(path):
                return path
    except Exception:
        pass
    return None


def convert_via_node(input_file, output_file):
    """Try Node.js jsonld conversion. Returns True on success, False on any failure."""
    node_modules = _get_npm_global_modules()
    if not node_modules:
        print("npm root -g failed — skipping Node.js path")
        return False

    jsonld_path = os.path.join(node_modules, 'jsonld')
    if not os.path.isdir(jsonld_path):
        print("jsonld package not found at %s — skipping Node.js path" % jsonld_path)
        return False

    tmp_js = None
    try:
        fd, tmp_js = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w') as f:
            f.write(_CONVERT_JS)

        env = os.environ.copy()
        env['NODE_PATH'] = node_modules

        r = subprocess.run(
            ['node', tmp_js, input_file, output_file],
            capture_output=True, text=True, timeout=300, env=env
        )
        if r.returncode == 0:
            print(r.stdout.strip())
            return True
        else:
            print("Node.js conversion failed: %s" % r.stderr.strip())
            return False
    except subprocess.TimeoutExpired:
        print("Node.js conversion timed out after 300s")
        return False
    except Exception as e:
        print("Node.js conversion exception: %s" % e)
        return False
    finally:
        if tmp_js and os.path.exists(tmp_js):
            try:
                os.unlink(tmp_js)
            except Exception:
                pass


def convert_via_rdflib(input_file, output_file):
    """Fallback: rdflib-based conversion (slow for large files)."""
    from rdflib import Graph
    print("Loading JSON-LD from: %s" % input_file)
    g = Graph()
    print("Parsing JSON-LD (this may take a while for large files)...")
    g.parse(input_file, format='json-ld')
    print("Loaded %d triples" % len(g))
    print("Writing N-Triples to: %s" % output_file)
    g.serialize(destination=output_file, format='nt')
    print("Conversion complete!")


def convert_jsonld_to_ntriples(input_file, output_file):
    """Convert JSON-LD to N-Triples, trying Node.js first then rdflib."""
    print("Converting: %s" % input_file)
    if convert_via_node(input_file, output_file):
        return
    print("Falling back to rdflib...")
    convert_via_rdflib(input_file, output_file)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_to_ntriples.py <input.jsonld> <output.nt>")
        sys.exit(1)
    convert_jsonld_to_ntriples(sys.argv[1], sys.argv[2])
