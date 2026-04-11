#!/usr/bin/env python3
"""Brick Ontology MCP Server - tools for exploring, querying, validating,
and creating Brick building models."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

import brickschema
from mcp.server.fastmcp import FastMCP
from rdflib import URIRef, Literal, Namespace
from rdflib.namespace import RDF as _RDF, RDFS as _RDFS, OWL as _OWL, SKOS as _SKOS

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
BRICK_NS = Namespace("https://brickschema.org/schema/Brick#")
BSH_NS = Namespace("https://brickschema.org/schema/BrickShape#")
TAG_NS = Namespace("https://brickschema.org/schema/BrickTag#")
REC_NS = Namespace("https://w3id.org/rec#")
SH_NS = Namespace("http://www.w3.org/ns/shacl#")

STANDARD_PREFIXES = """\
PREFIX brick: <https://brickschema.org/schema/Brick#>
PREFIX bsh: <https://brickschema.org/schema/BrickShape#>
PREFIX tag: <https://brickschema.org/schema/BrickTag#>
PREFIX rec: <https://w3id.org/rec#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX ref: <https://brickschema.org/schema/Brick/ref#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# ---------------------------------------------------------------------------
# Load Brick ontology once at module startup
# ---------------------------------------------------------------------------

mcp = FastMCP("brick-ontology-explorer")

_ONTOLOGY: brickschema.Graph = brickschema.Graph(load_brick=True, brick_version="1.4")


def _get_ontology() -> brickschema.Graph:
    return _ONTOLOGY


def _format_uri(uri: str | URIRef) -> str:
    """Convert a full URI to a prefixed shortform."""
    s = str(uri)
    replacements = [
        ("https://brickschema.org/schema/Brick#", "brick:"),
        ("https://brickschema.org/schema/BrickTag#", "tag:"),
        ("https://brickschema.org/schema/BrickShape#", "bsh:"),
        ("https://w3id.org/rec#", "rec:"),
        ("http://www.w3.org/2000/01/rdf-schema#", "rdfs:"),
        ("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf:"),
        ("http://www.w3.org/2002/07/owl#", "owl:"),
        ("http://www.w3.org/2004/02/skos/core#", "skos:"),
        ("http://www.w3.org/ns/shacl#", "sh:"),
        ("https://brickschema.org/schema/Brick/ref#", "ref:"),
    ]
    for full, short in replacements:
        if s.startswith(full):
            return short + s[len(full):]
    return s


def _resolve_class_name(name: str, g: brickschema.Graph) -> URIRef | None:
    """Resolve 'Chiller', 'brick:Chiller', 'rec:ObservationEvent', or full URI to a URIRef.

    Returns the URIRef if the class exists in the ontology, else None.
    """
    clean = name.strip()
    if clean.startswith("brick:"):
        clean = clean[6:]
        search_ns = [BRICK_NS]
    elif clean.startswith("rec:"):
        clean = clean[4:]
        search_ns = [REC_NS]
    elif clean.startswith("https://brickschema.org/schema/Brick#"):
        clean = clean[len("https://brickschema.org/schema/Brick#"):]
        search_ns = [BRICK_NS]
    elif clean.startswith("https://w3id.org/rec#"):
        clean = clean[len("https://w3id.org/rec#"):]
        search_ns = [REC_NS]
    else:
        search_ns = [BRICK_NS, REC_NS]

    clean = clean.replace(" ", "_")

    for ns in search_ns:
        uri = ns[clean]
        if (uri, _RDF.type, _OWL.Class) in g:
            return uri

    # Case-insensitive label / local name search across both namespaces
    sparql = STANDARD_PREFIXES + f"""
SELECT ?cls WHERE {{
    ?cls rdf:type owl:Class .
    FILTER(
        STRSTARTS(STR(?cls), STR(brick:))
        || STRSTARTS(STR(?cls), STR(rec:))
    )
    OPTIONAL {{ ?cls rdfs:label ?lbl }}
    FILTER(
        LCASE(STR(?lbl)) = LCASE("{clean.replace("_", " ")}")
        || LCASE(REPLACE(STR(?cls), ".*#", "")) = LCASE("{clean}")
    )
}}
LIMIT 1
"""
    results = list(g.query(sparql))
    if results:
        return results[0][0]
    return None


def _add_prefixes(query: str) -> str:
    """Prepend standard prefixes if the query has none."""
    if "PREFIX" in query.upper():
        return query
    return STANDARD_PREFIXES + "\n" + query


def _format_results_table(results, var_names: list[str]) -> str:
    """Format SPARQL results as a simple text table."""
    rows = []
    for row in results:
        cells = []
        for val in row:
            if val is None:
                cells.append("")
            elif isinstance(val, Literal):
                cells.append(str(val))
            else:
                cells.append(_format_uri(val))
        rows.append(cells)

    if not rows:
        return "Ingen resultater fundet."

    col_widths = [
        max(len(h), max((len(r[i]) for r in rows if i < len(r)), default=0))
        for i, h in enumerate(var_names)
    ]

    lines = []
    lines.append(" | ".join(h.ljust(col_widths[i]) for i, h in enumerate(var_names)))
    lines.append("-+-".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(" | ".join(
            (row[i] if i < len(row) else "").ljust(col_widths[i])
            for i in range(len(var_names))
        ))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool Group 1: Explore Ontology
# ---------------------------------------------------------------------------

@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_search(query: str, limit: int = 20) -> str:
    """Søg efter Brick- og REC-klasser ud fra et nøgleord.

    Søger case-insensitivt i klasse-navne og rdfs:label i både brick:- og rec:-namespace.
    Returnerer klasse-navn, label og umiddelbar forældreklasse.

    Args:
        query: Søgeord, f.eks. "temperature", "AHU", "ObservationEvent", "valve"
        limit: Maks antal resultater (default 20)
    """
    g = _get_ontology()
    sparql = STANDARD_PREFIXES + f"""
SELECT DISTINCT ?cls ?label ?parent WHERE {{
    ?cls rdf:type owl:Class .
    FILTER(
        STRSTARTS(STR(?cls), STR(brick:))
        || STRSTARTS(STR(?cls), STR(rec:))
    )
    OPTIONAL {{ ?cls rdfs:label ?label }}
    OPTIONAL {{
        ?cls rdfs:subClassOf ?parent .
        FILTER(
            STRSTARTS(STR(?parent), STR(brick:))
            || STRSTARTS(STR(?parent), STR(rec:))
        )
    }}
    FILTER(
        CONTAINS(LCASE(STR(?label)), LCASE("{query}"))
        || CONTAINS(LCASE(REPLACE(STR(?cls), ".*#", "")), LCASE("{query}"))
    )
}}
ORDER BY ?cls
LIMIT {limit}
"""
    results = list(g.query(sparql))
    if not results:
        return f"Ingen klasser fundet for '{query}'."

    lines = [f"Søgeresultater for '{query}' ({len(results)} fundet):\n"]
    for row in results:
        cls_short = _format_uri(row[0])
        local = cls_short.replace("brick:", "").replace("rec:", "").replace("_", " ")
        label = str(row[1]) if row[1] else local
        parent = _format_uri(row[2]) if row[2] else ""
        line = f"  {cls_short}"
        if label and label.lower() != local.lower():
            line += f"  [{label}]"
        if parent:
            line += f"  (under {parent})"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_hierarchy(class_name: str, direction: str = "descendants", depth: int = 3) -> str:
    """Vis klassehierarkiet for en Brick-klasse som et træ.

    Args:
        class_name: Klassenavn, f.eks. "Sensor", "brick:Equipment", "Chiller"
        direction: "descendants" (børneklasser) eller "ancestors" (forældreklasser)
        depth: Maksimal dybde for descendants (default 3, brug -1 for ubegrænset)
    """
    g = _get_ontology()
    uri = _resolve_class_name(class_name, g)
    if uri is None:
        return f"Klassen '{class_name}' findes ikke. Brug brick_search for at finde det korrekte navn."

    short = _format_uri(uri)

    if direction == "ancestors":
        sparql = STANDARD_PREFIXES + f"""
SELECT DISTINCT ?child ?parent WHERE {{
    <{uri}> rdfs:subClassOf+ ?anc .
    ?anc rdfs:subClassOf* ?parent .
    ?child rdfs:subClassOf ?parent .
    FILTER(STRSTARTS(STR(?child), STR(brick:)))
    FILTER(STRSTARTS(STR(?parent), STR(brick:)))
    FILTER(?parent != owl:Thing)
    FILTER(?child = <{uri}> || EXISTS {{ <{uri}> rdfs:subClassOf+ ?child }})
}}
"""
        results = list(g.query(sparql))
        children_map: dict[str, list[str]] = {}
        for row in results:
            c = _format_uri(row[0])
            p = _format_uri(row[1])
            children_map.setdefault(p, [])
            if c not in children_map[p]:
                children_map[p].append(c)

        all_children = {c for cs in children_map.values() for c in cs}
        all_nodes = set(children_map.keys()) | all_children
        roots = all_nodes - all_children

        lines = [f"Forfædreklasser for {short}:\n"]

        def render(node: str, prefix: str = "", is_last: bool = True):
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + node)
            children = sorted(children_map.get(node, []))
            for i, child in enumerate(children):
                ext = "    " if is_last else "│   "
                render(child, prefix + ext, i == len(children) - 1)

        for root in sorted(roots):
            render(root)
        return "\n".join(lines)

    # descendants
    sparql = STANDARD_PREFIXES + f"""
SELECT DISTINCT ?child ?parent WHERE {{
    ?child rdfs:subClassOf+ <{uri}> .
    ?child rdfs:subClassOf ?parent .
    FILTER(STRSTARTS(STR(?child), STR(brick:)))
    FILTER(
        STRSTARTS(STR(?parent), STR(brick:))
        || ?parent = <{uri}>
    )
}}
"""
    results = list(g.query(sparql))
    if not results:
        return f"{short} har ingen subklasser."

    children_map: dict[str, list[str]] = {}
    for row in results:
        child = _format_uri(row[0])
        parent = _format_uri(row[1])
        children_map.setdefault(parent, [])
        if child not in children_map[parent]:
            children_map[parent].append(child)

    total = len({c for cs in children_map.values() for c in cs})
    lines = [f"Subklasser af {short} ({total} klasser, dybde {depth if depth != -1 else 'ubegrænset'}):\n"]

    def render_desc(node: str, prefix: str = "", current_depth: int = 0):
        if depth != -1 and current_depth >= depth:
            remaining = children_map.get(node, [])
            if remaining:
                lines.append(prefix + f"    ... ({len(remaining)} subklasser - brug depth={current_depth+1} for at se mere)")
            return
        children = sorted(children_map.get(node, []))
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + child)
            ext = "    " if is_last else "│   "
            render_desc(child, prefix + ext, current_depth + 1)

    render_desc(short)
    return "\n".join(lines)


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_describe(class_name: str) -> str:
    """Vis detaljeret beskrivelse af en Brick- eller REC-klasse.

    Viser label, definition, forældreklasser, SHACL properties, tilknyttede
    tags, deprecation-info og URI. Understøtter både brick:- og rec:-namespace.

    Args:
        class_name: Klassenavn, f.eks. "Air_Handling_Unit", "brick:Chiller", "rec:ObservationEvent"
    """
    g = _get_ontology()
    uri = _resolve_class_name(class_name, g)
    if uri is None:
        return f"Klassen '{class_name}' findes ikke. Brug brick_search for at finde det korrekte navn."

    short = _format_uri(uri)
    lines = [f"=== {short} ===\n"]

    for obj in g.objects(uri, _RDFS.label):
        lines.append(f"Label: {obj}")
        break

    for obj in g.objects(uri, _SKOS.definition):
        lines.append(f"Definition: {obj}")
        break

    # Deprecation
    for obj in g.objects(uri, _OWL.deprecated):
        if str(obj).lower() == "true":
            lines.append("\n⚠ DEPRECATED")
            for msg in g.objects(uri, BRICK_NS.deprecationMitigationMessage):
                lines.append(f"  Mitigering: {msg}")
            for repl in g.objects(uri, BRICK_NS.isReplacedBy):
                lines.append(f"  Erstattet af: {_format_uri(repl)}")
        break

    # Parent classes
    parents = sorted(
        _format_uri(p)
        for p in g.objects(uri, _RDFS.subClassOf)
        if isinstance(p, URIRef) and str(p) != str(_OWL.Thing)
    )
    if parents:
        lines.append("\nForældreklasser:")
        for p in parents:
            lines.append(f"  - {p}")

    # Equivalent classes
    equiv = [_format_uri(e) for e in g.objects(uri, _OWL.equivalentClass) if isinstance(e, URIRef)]
    if equiv:
        lines.append("\nÆkvivalente klasser (aliaser):")
        for e in equiv:
            lines.append(f"  - {e}")

    # Associated tags
    tags = sorted(_format_uri(t).replace("tag:", "") for t in g.objects(uri, BRICK_NS.hasAssociatedTag))
    if tags:
        lines.append(f"\nTags: {', '.join(tags)}")

    # Quantity / Substance
    for q in g.objects(uri, BRICK_NS.hasQuantity):
        lines.append(f"\nMåleenhed (hasQuantity): {_format_uri(q)}")
        break
    for s in g.objects(uri, BRICK_NS.hasSubstance):
        lines.append(f"Stof (hasSubstance): {_format_uri(s)}")
        break

    # SHACL properties
    sh_props = []
    for shape in g.objects(uri, SH_NS.property):
        prop_path = prop_class = prop_min = prop_max = None
        for p, o in g.predicate_objects(shape):
            if p == SH_NS.path:
                prop_path = _format_uri(o)
            elif p == SH_NS["class"]:
                prop_class = _format_uri(o)
            elif p == SH_NS.minCount:
                prop_min = str(o)
            elif p == SH_NS.maxCount:
                prop_max = str(o)
        if prop_path:
            entry = f"  {prop_path}"
            if prop_class:
                entry += f" -> {prop_class}"
            if prop_min or prop_max:
                entry += f" [{prop_min or '0'}..{prop_max or '*'}]"
            sh_props.append(entry)

    if sh_props:
        lines.append("\nProperties (SHACL shapes):")
        for p in sorted(sh_props):
            lines.append(p)

    lines.append(f"\nURI: {uri}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool Group 2: SPARQL Queries
# ---------------------------------------------------------------------------

SPARQL_EXAMPLES: dict[str, list[dict]] = {
    "equipment": [
        {
            "title": "List alle HVAC-udstyr typer (direkte subklasser)",
            "query": "SELECT ?cls ?label WHERE {\n  ?cls rdfs:subClassOf brick:HVAC_Equipment ;\n       rdf:type owl:Class .\n  OPTIONAL { ?cls rdfs:label ?label }\n}\nORDER BY ?cls",
        },
        {
            "title": "Find alle subklasser af AHU (transitivt)",
            "query": "SELECT ?cls WHERE {\n  ?cls rdfs:subClassOf+ brick:Air_Handling_Unit .\n  FILTER(STRSTARTS(STR(?cls), STR(brick:)))\n}\nORDER BY ?cls",
        },
        {
            "title": "Vis alle top-level Equipment klasser",
            "query": "SELECT ?cls ?label WHERE {\n  ?cls rdfs:subClassOf brick:Equipment ;\n       rdf:type owl:Class .\n  OPTIONAL { ?cls rdfs:label ?label }\n  FILTER NOT EXISTS {\n    ?cls rdfs:subClassOf ?mid .\n    ?mid rdfs:subClassOf brick:Equipment .\n    FILTER(?mid != brick:Equipment)\n  }\n}\nORDER BY ?cls",
        },
    ],
    "points": [
        {
            "title": "List alle sensor-typer",
            "query": "SELECT ?cls ?label WHERE {\n  ?cls rdfs:subClassOf* brick:Sensor ;\n       rdf:type owl:Class .\n  OPTIONAL { ?cls rdfs:label ?label }\n}\nORDER BY ?cls",
        },
        {
            "title": "Find temperature-relaterede sensors",
            "query": "SELECT ?cls ?label WHERE {\n  ?cls rdfs:subClassOf+ brick:Sensor ;\n       rdf:type owl:Class .\n  FILTER(CONTAINS(LCASE(STR(?cls)), 'temperature'))\n  OPTIONAL { ?cls rdfs:label ?label }\n}\nORDER BY ?cls",
        },
        {
            "title": "Find alle Point-subkategorier",
            "query": "SELECT ?cls WHERE {\n  ?cls rdfs:subClassOf brick:Point ;\n       rdf:type owl:Class .\n  FILTER(STRSTARTS(STR(?cls), STR(brick:)))\n}\nORDER BY ?cls",
        },
    ],
    "locations": [
        {
            "title": "List RealEstateCore space-typer (Brick 1.4)",
            "query": "SELECT ?cls ?label WHERE {\n  ?cls rdf:type owl:Class .\n  FILTER(STRSTARTS(STR(?cls), STR(rec:)))\n  OPTIONAL { ?cls rdfs:label ?label }\n}\nORDER BY ?cls",
        },
        {
            "title": "List Brick Location klasser (deprecated i 1.4, men stadig til stede)",
            "query": "SELECT ?cls ?label WHERE {\n  ?cls rdfs:subClassOf* brick:Location ;\n       rdf:type owl:Class .\n  OPTIONAL { ?cls rdfs:label ?label }\n}\nORDER BY ?cls",
        },
    ],
    "relationships": [
        {
            "title": "List alle Brick object properties",
            "query": "SELECT ?prop ?label WHERE {\n  ?prop rdf:type owl:ObjectProperty .\n  FILTER(STRSTARTS(STR(?prop), STR(brick:)))\n  OPTIONAL { ?prop rdfs:label ?label }\n}\nORDER BY ?prop",
        },
        {
            "title": "Find domain og range for brick:feeds",
            "query": "SELECT ?domain ?range WHERE {\n  brick:feeds rdfs:domain ?domain ;\n              rdfs:range ?range .\n}",
        },
        {
            "title": "Find SHACL properties for en klasse (erstat AHU-klassen)",
            "query": "SELECT ?path ?targetClass WHERE {\n  brick:Air_Handling_Unit rdfs:subClassOf*/sh:property ?shape .\n  ?shape sh:path ?path .\n  OPTIONAL { ?shape sh:class ?targetClass }\n}",
        },
    ],
}


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_sparql_examples(category: str = "all") -> str:
    """Vis kuraterede SPARQL-eksempel queries for Brick-ontologien.

    Args:
        category: "equipment", "points", "locations", "relationships", eller "all"
    """
    categories = list(SPARQL_EXAMPLES.keys()) if category == "all" else [category]

    lines = []
    for cat in categories:
        if cat not in SPARQL_EXAMPLES:
            return f"Ukendt kategori '{cat}'. Vælg: equipment, points, locations, relationships, all"
        lines.append(f"\n## {cat.capitalize()}\n")
        for ex in SPARQL_EXAMPLES[cat]:
            lines.append(f"### {ex['title']}")
            lines.append("```sparql")
            lines.append(ex["query"])
            lines.append("```\n")

    return "\n".join(lines)


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_run_sparql(query: str, file_path: Optional[str] = None, limit: int = 50) -> str:
    """Kør en SPARQL SELECT-query mod Brick-ontologien (og evt. en bruger-model).

    Standard prefixes (brick:, rdf:, rdfs:, owl:, skos:, rec:, etc.) tilføjes
    automatisk hvis de ikke allerede er i queryen.

    Args:
        query: SPARQL SELECT query
        file_path: Valgfri sti til en .ttl model-fil der loades oveni ontologien
        limit: Maks antal rækker (default 50). Tilføjes automatisk hvis LIMIT mangler.
    """
    g = _get_ontology()

    if file_path:
        if not os.path.exists(file_path):
            return f"Fil ikke fundet: {file_path}"
        combined = brickschema.Graph(load_brick=True, brick_version="1.4")
        try:
            combined.load_file(file_path)
        except Exception as e:
            return f"Fejl ved indlæsning af {file_path}: {e}"
        target = combined
    else:
        target = g

    full_query = _add_prefixes(query)

    upper = full_query.upper()
    if "LIMIT" not in upper:
        full_query = full_query.rstrip() + f"\nLIMIT {limit}"

    try:
        results = target.query(full_query)
    except Exception as e:
        return f"SPARQL-fejl: {e}\n\nQuery:\n{full_query}"

    var_names = [str(v) for v in results.vars] if hasattr(results, "vars") else []
    rows = list(results)

    if not rows:
        return "Forespørgslen returnerede ingen resultater."

    table = _format_results_table(rows, var_names)
    return f"{len(rows)} resultat(er):\n\n{table}"


# ---------------------------------------------------------------------------
# Tool Group 3: Validate Files
# ---------------------------------------------------------------------------

@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_validate_file(file_path: str) -> str:
    """Valider en Brick TTL-fil mod SHACL shapes.

    ADVARSEL: Validering tager typisk 20-30 sekunder grundet SHACL-behandling.
    Kendte QUDT QuantityKind false positives filtreres automatisk fra.

    Args:
        file_path: Sti til .ttl filen der skal valideres
    """
    if not os.path.exists(file_path):
        return f"Fil ikke fundet: {file_path}"

    try:
        g = brickschema.Graph(load_brick=True, brick_version="1.4")
        g.load_file(file_path)
    except Exception as e:
        return f"Fejl ved indlæsning af {file_path}: {e}"

    try:
        conforms, results_graph, report = g.validate()
    except Exception as e:
        return f"Fejl under validering: {e}"

    if conforms:
        return f"✓ {file_path} er valid og overholder Brick-ontologien."

    SH = Namespace("http://www.w3.org/ns/shacl#")
    violations = []

    for result in results_graph.subjects(_RDF.type, SH.ValidationResult):
        severity = str(results_graph.value(result, SH.resultSeverity) or "")
        focus = str(results_graph.value(result, SH.focusNode) or "")
        source = str(results_graph.value(result, SH.sourceShape) or "")
        message = str(results_graph.value(result, SH.resultMessage) or "")
        value = str(results_graph.value(result, SH.value) or "")

        # Filter known QUDT false positives
        if "QuantityKind" in message or ("qudt" in source.lower() and "bsh" not in source.lower()):
            continue

        violations.append({
            "severity": _format_uri(severity),
            "focus": _format_uri(focus),
            "source": _format_uri(source),
            "message": message,
            "value": _format_uri(value) if value else "",
        })

    if not violations:
        return f"✓ {file_path} er valid (kun kendte QUDT-violations ignoreret)."

    lines = [f"✗ {file_path} har {len(violations)} violation(er):\n"]
    for i, v in enumerate(violations[:20], 1):
        lines.append(f"--- Violation {i} [{v['severity']}] ---")
        lines.append(f"  FocusNode: {v['focus']}")
        lines.append(f"  Shape:     {v['source']}")
        if v["message"]:
            lines.append(f"  Besked:    {v['message']}")
        if v["value"]:
            lines.append(f"  Værdi:     {v['value']}")
        lines.append("")

    if len(violations) > 20:
        lines.append(f"... og {len(violations) - 20} yderligere violations.")

    return "\n".join(lines)


@mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True})
def brick_validate_ttl(ttl_content: str) -> str:
    """Valider TTL-indhold (som string) og giv konkrete fix-forslag.

    Bruges til at validere model-TTL der er under oprettelse, inden det skrives til fil.
    ADVARSEL: Validering tager typisk 20-30 sekunder.

    Args:
        ttl_content: TTL-indhold som streng
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False, encoding="utf-8") as f:
        f.write(ttl_content)
        tmp_path = f.name

    try:
        result = brick_validate_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    suggestions = []
    if "sh:NodeConstraintComponent" in result:
        suggestions.append("• Tjek at alle entiteter har korrekt rdf:type med en Brick-klasse")
    if "sh:ClassConstraintComponent" in result:
        suggestions.append("• En property peger på en forkert type. Brug brick_describe for at se korrekte target-klasser")
    if "sh:MinCountConstraintComponent" in result:
        suggestions.append("• En påkrævet property mangler. Brug brick_describe for at se hvad der kræves")
    if "sh:MaxCountConstraintComponent" in result:
        suggestions.append("• En property er angivet for mange gange")

    if suggestions:
        result += "\n\n### Fix-forslag:\n" + "\n".join(suggestions)

    return result


# ---------------------------------------------------------------------------
# Tool Group 4: Generate Models
# ---------------------------------------------------------------------------

@mcp.tool()
def brick_generate_model(
    building_name: str,
    entities: list,
    namespace: str = "http://example.org/building#",
) -> str:
    """Generer en Brick TTL-bygningsmodel fra struktureret input.

    Validerer at alle Brick-klassenavne eksisterer inden generering.

    Args:
        building_name: Navn til bygningen
        entities: Liste af entitets-dicts, hver med felterne:
            - id (str, påkrævet): Unikt instans-navn, f.eks. "ahu_1"
            - type (str, påkrævet): Brick-klassenavn, f.eks. "Air_Handling_Unit"
            - label (str, valgfrit): Menneskevenligt navn
            - hasPoint (list[str], valgfrit): Liste af point instans-id'er
            - feeds (list[str], valgfrit): Id'er dette udstyr feeder
            - hasLocation (str, valgfrit): Locations instans-id
            - hasPart (list[str], valgfrit): Sub-entitets id'er
        namespace: Namespace URI (default: http://example.org/building#)
    """
    g = _get_ontology()

    errors = []
    for ent in entities:
        if not isinstance(ent, dict):
            errors.append(f"Ugyldig entitet: {ent} (skal være en dict)")
            continue
        if "id" not in ent:
            errors.append(f"Entitet mangler 'id' felt: {ent}")
        if "type" not in ent:
            errors.append(f"Entitet '{ent.get('id', '?')}' mangler 'type' felt")
            continue
        uri = _resolve_class_name(ent["type"], g)
        if uri is None:
            errors.append(
                f"Klassen '{ent['type']}' for entitet '{ent.get('id', '?')}' "
                f"findes ikke i Brick. Brug brick_search for at finde det korrekte navn."
            )

    if errors:
        return "Fejl - kan ikke generere model:\n" + "\n".join(f"• {e}" for e in errors)

    ns = namespace.rstrip("/").rstrip("#") + "#"
    lines = [
        f"# Brick bygningsmodel: {building_name}",
        f"# Genereret med brick-ontology-explorer plugin",
        "",
        f"@prefix bldg: <{ns}> .",
        "@prefix brick: <https://brickschema.org/schema/Brick#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix rec: <https://w3id.org/rec#> .",
        "@prefix ref: <https://brickschema.org/schema/Brick/ref#> .",
        "",
        f"# Ontologi-deklaration",
        f"<{ns.rstrip('#')}> rdf:type owl:Ontology ;",
        f'    rdfs:label "{building_name}" .',
        "",
    ]

    for ent in entities:
        ent_id = ent["id"]
        brick_class_uri = _resolve_class_name(ent["type"], g)
        brick_class_short = _format_uri(brick_class_uri)
        bldg_ref = f"bldg:{ent_id}"

        props = [f"    a {brick_class_short}"]

        if "label" in ent:
            props.append(f'    rdfs:label "{ent["label"]}"')

        for point_id in ent.get("hasPoint", []):
            props.append(f"    brick:hasPoint bldg:{point_id}")

        for fed_id in ent.get("feeds", []):
            props.append(f"    brick:feeds bldg:{fed_id}")

        if "hasLocation" in ent:
            props.append(f"    brick:hasLocation bldg:{ent['hasLocation']}")

        for part_id in ent.get("hasPart", []):
            props.append(f"    brick:hasPart bldg:{part_id}")

        ttl_block = f"{bldg_ref}\n" + " ;\n".join(props) + " ."
        lines.append(ttl_block)
        lines.append("")

    ttl = "\n".join(lines)
    ttl += "\n# Tip: Brug brick_validate_ttl til at validere denne model."
    return ttl


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
