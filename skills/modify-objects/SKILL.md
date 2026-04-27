---
name: modify-objects
description: Add new entities to an existing Brick TTL model, or update existing entities (change type, add/remove properties). Use when the user wants to extend or edit a building model file — e.g. "add a VAV box to the AHU", "give this sensor a label", "change this entity's type", "the AHU has another point I forgot".
---

# Tilføj eller opdatér objekter i en Brick-model

Brug `brick_add_objects` til at tilføje **nye** entiteter, og `brick_update_objects` til at ændre **eksisterende** entiteter i en `.ttl`-fil.

Begge tools skriver direkte til filen som default (`write=True`). Sæt `write=False` for at se den ændrede TTL uden at gemme — nyttigt til tør-kørsel inden destruktive ændringer.

## Workflow

1. **Læs den eksisterende model** for at forstå hvilke entiteter og namespaces der findes (brug `Read` eller en SPARQL-query med `brick_run_sparql(file_path=...)`).
2. **Find de korrekte Brick-klasser** med `brick_search` og `brick_describe` for nye entiteter eller for ny type i replace-mode.
3. **Vælg det rette tool**:
   - Nyt id der ikke findes i modellen → `brick_add_objects`
   - Eksisterende id der skal ændres → `brick_update_objects`
4. **Udfør ændringen** (default skriver til fil).
5. **Validér ALTID efter** med `brick_validate_file(file_path)` — dette tager 20-30 sek og er ikke automatisk. Informér brugeren om ventetiden inden.

## brick_add_objects

Bruger samme entitets-format som `brick_generate_model`:

```python
brick_add_objects(
    file_path="/sti/til/bygning.ttl",
    entities=[
        {
            "id": "vav_3",
            "type": "Variable_Air_Volume_Box",
            "label": "VAV 3",
            "hasPoint": ["vav3_flow_sensor", "vav3_damper_pos"],
        },
        {"id": "vav3_flow_sensor", "type": "Supply_Air_Flow_Sensor"},
        {"id": "vav3_damper_pos", "type": "Damper_Position_Sensor"},
    ],
)
```

Fejler hvis:
- Filen ikke findes
- En klasse er ukendt (brug `brick_search`)
- Et id allerede findes i modellen → brug `brick_update_objects` i stedet

## brick_update_objects — vælg mode bevidst

`mode` er **påkrævet** og styrer hvor destruktiv ændringen er:

### `mode="append"` — tilføj triples uden at fjerne noget

Brug når du tilføjer information uden at ville fjerne noget eksisterende. F.eks. tilføj en glemt `hasPoint` til en AHU:

```python
brick_update_objects(
    file_path="/sti/til/bygning.ttl",
    mode="append",
    entities=[
        {
            "id": "ahu_1",
            "type": "Air_Handling_Unit",   # samme type som før
            "hasPoint": ["new_point_id"],  # tilføjes til de eksisterende
        },
    ],
)
```

OBS: `type` skal være med (entitets-formatet kræver det), og det skal matche den eksisterende type — ellers ender entiteten med to typer i `append`-mode.

### `mode="replace"` — slet alle eksisterende triples for entiteten, opret på ny

Brug når entiteten skal rettes fundamentalt — forkert type, forkert sæt af properties, eller en oprydning. Alle triples med entiteten som subject slettes først, derefter genskabes entiteten ud fra det angivne dict.

```python
brick_update_objects(
    file_path="/sti/til/bygning.ttl",
    mode="replace",
    entities=[
        {
            "id": "sensor_42",
            "type": "Supply_Air_Temperature_Sensor",  # rettet fra Temperature_Sensor
            "label": "SAT Sensor 42",
        },
    ],
)
```

Vigtigt: `replace` fjerner KUN triples hvor entiteten er subject. Andre entiteters references til denne (f.eks. `<andet> brick:hasPoint <denne>`) bevares.

## Valg af mode — kort

| Situation | Mode |
|-----------|------|
| Tilføj endnu en `hasPoint`, `feeds`, eller `hasPart` | `append` |
| Tilføj en label til en entitet der mangler en | `append` |
| Ret en forkert `rdf:type` | `replace` |
| Rens et helt sæt forkerte properties op | `replace` |
| Skift en entitets sæt af `hasPoint` til en helt anden liste | `replace` |

Hvis du er i tvivl: kør først med `write=False` og se det resulterende TTL.

## Auto-detekteret namespace

Bygnings-namespacet (`bldg:`) detekteres automatisk fra filens `@prefix bldg:` deklaration. Hvis filen bruger et andet prefix end `bldg:`, angiv `namespace=...` eksplicit.

## Husk validering

Modify-operationer validerer kun klassenavne og id-eksistens. Strukturelle SHACL-fejl (forkerte target-klasser, manglende påkrævede properties) opdages først af `brick_validate_file`. Kør den efter hver ændring og advar brugeren om de 20-30 sek ventetid.
