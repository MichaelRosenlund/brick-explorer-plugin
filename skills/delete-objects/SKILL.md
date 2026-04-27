---
name: delete-objects
description: Delete entities from an existing Brick TTL model, including cleanup of references that pointed at the deleted entities. Use when the user wants to remove equipment, points, locations, or other objects from a building model — e.g. "remove the old AHU", "delete these obsolete sensors", "drop this VAV box and its points".
---

# Slet objekter fra en Brick-model

Brug `brick_delete_objects` til at fjerne entiteter fra en eksisterende `.ttl`-fil. Tool'et skriver direkte til filen som default (`write=True`); sæt `write=False` for tør-kørsel.

## Workflow

1. **Identificér hvad der skal slettes** — spørg brugeren om id'er eller find dem via SPARQL.
2. **Find afhængigheder først** med en SPARQL-query — så ved du om sletningen rammer mere end forventet:
   ```python
   brick_run_sparql(
       query='''
           SELECT ?subj ?pred WHERE {
               ?subj ?pred bldg:ahu_1 .
           }
       ''',
       file_path="/sti/til/bygning.ttl",
   )
   ```
3. **Beslut om relaterede entiteter også skal slettes** — sletning er IKKE kaskaderende på "tilhørende" objekter. Hvis du sletter en AHU, slettes dens points ikke automatisk; du skal angive deres id'er eksplicit.
4. **Kald `brick_delete_objects`** med id'erne (uden `bldg:`-prefix).
5. **Validér efter** med `brick_validate_file` (20-30 sek). Informér brugeren om ventetiden.

## Eksempel

```python
brick_delete_objects(
    file_path="/sti/til/bygning.ttl",
    ids=["ahu_1", "ahu_1_sat_sensor", "ahu_1_rat_sensor"],
)
```

## `cleanup_references` — næsten altid True

Default `True` rydder også triples op hvor de slettede entiteter optræder som object. Eksempel: hvis `bldg:floor_1 brick:hasPart bldg:vav_3` findes og du sletter `vav_3`, fjernes også den triple — ellers bliver der en dangling reference der vil få `brick_validate_file` til at fejle.

Sæt kun `cleanup_references=False` ved bevidste mellemtrin, f.eks. når du vil slette en entitet og straks erstatte den med en med samme id (i hvilket tilfælde du dog hellere skal bruge `brick_update_objects` med `mode="replace"`).

## Kaskade-effekter — pas på

| Du sletter | Risiko |
|------------|--------|
| Et udstyr (AHU, VAV osv.) | Dens points er nu forældreløse — slet dem også, eller flyt dem til andet udstyr via `brick_update_objects` |
| En lokation (`rec:Level`, `rec:Room`) | Udstyr/points med `brick:hasLocation` mister deres lokationsreference (cleanup_references rydder triplen, men entiteten selv består uden lokation) |
| Et point | Refererende `brick:hasPoint` på udstyret rydddes (med default cleanup) |

Når brugeren beder om at "slette et udstyr og alt der hører til det", brug først SPARQL til at finde alle `hasPoint`/`hasPart`-relaterede id'er, og inkludér dem i `ids`-listen.

## Auto-detekteret namespace

`bldg:`-prefixet detekteres automatisk fra filen. Angiv `namespace=...` hvis filen bruger et andet prefix.

## Husk validering

Sletning kan efterlade ugyldige tilstande (f.eks. udstyr der mister en påkrævet property). Kør `brick_validate_file` efter sletningen og fix eventuelle violations.
