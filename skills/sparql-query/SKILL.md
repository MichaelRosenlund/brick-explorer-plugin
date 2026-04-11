---
name: sparql-query
description: Build and run SPARQL queries against the Brick ontology or user building models. Use when the user wants to query Brick data, explore patterns in building models, needs help writing SPARQL for RDF/Brick data, or wants to understand what queries are possible.
---

# SPARQL-queries mod Brick-ontologien

Brug MCP-toolsene `brick_run_sparql` og `brick_sparql_examples` til at query Brick-data.

## Workflow

1. **Nye brugere** → start med `brick_sparql_examples("all")` for at vise hvad der er muligt
2. **Byg queries inkrementelt** – start simpelt, tilføj constraints gradvist
3. **Mod ontologien** → `brick_run_sparql(query)` uden `file_path`
4. **Mod en model** → `brick_run_sparql(query, file_path="/sti/til/model.ttl")`

## Auto-bundne prefixes

Alle queries får automatisk disse prefixes (behøver ikke skrives manuelt):
```sparql
PREFIX brick: <https://brickschema.org/schema/Brick#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX bsh: <https://brickschema.org/schema/BrickShape#>
PREFIX tag: <https://brickschema.org/schema/BrickTag#>
PREFIX rec: <https://w3id.org/rec#>
PREFIX ref: <https://brickschema.org/schema/Brick/ref#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
```

## Vigtige SPARQL-mønstre for Brick

### Find alle instanser af en type i en model
```sparql
SELECT ?entity WHERE {
  ?entity a brick:Air_Handling_Unit
}
```

### Find udstyr og tilhørende points
```sparql
SELECT ?equip ?point ?pointType WHERE {
  ?equip a/rdfs:subClassOf* brick:Equipment ;
         brick:hasPoint ?point .
  ?point a ?pointType .
}
```

### Find transitive subklasser
```sparql
SELECT ?cls WHERE {
  ?cls rdfs:subClassOf+ brick:Sensor .
  FILTER(STRSTARTS(STR(?cls), STR(brick:)))
}
```

### Find hvad der feeder hvad
```sparql
SELECT ?upstream ?downstream WHERE {
  ?upstream brick:feeds ?downstream .
}
```

### Find klasse-hierarki
```sparql
SELECT ?child ?parent WHERE {
  ?child rdfs:subClassOf ?parent .
  FILTER(STRSTARTS(STR(?child), STR(brick:)))
  FILTER(STRSTARTS(STR(?parent), STR(brick:)))
}
```

## Tips

- `rdfs:subClassOf+` = transitivt (alle niveauer ned)
- `rdfs:subClassOf*` = transitivt inkl. selve klassen
- `a/rdfs:subClassOf*` = instansen er af typen eller en subtype
- Brug `FILTER(STRSTARTS(STR(?x), STR(brick:)))` til at begrænse til Brick-namespace
- Default LIMIT er 50 – øg med `limit`-parameteren hvis nødvendigt
