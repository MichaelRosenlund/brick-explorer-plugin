---
name: validate-brick
description: Validate Brick building model TTL files against SHACL shapes. Use when the user has a .ttl file and wants to check if it conforms to the Brick schema, find errors in their model, or get suggestions for fixing validation issues.
---

# Valider Brick-modeller

Brug MCP-toolsene `brick_validate_file` og `brick_validate_ttl` til at validere Brick TTL-modeller.

## Workflow

1. **Eksisterende fil** → `brick_validate_file("/sti/til/model.ttl")`
2. **TTL-indhold** (under oprettelse) → `brick_validate_ttl(ttl_string)`
3. Gennemgå violations – de fleste har en klar besked om hvad der er galt
4. Brug `brick_describe` til at finde korrekte klasser og properties
5. Ret fejlene og valider igen

## ADVARSEL om tid

Validering tager **20-30 sekunder** grundet SHACL-behandling. Informér brugeren om dette inden validering startes.

## Kendte false positives (filtreres automatisk)

Brick 1.4's base-ontologi har kendte QUDT QuantityKind-violations. Disse filtreres automatisk fra og skal ignoreres.

## Typiske fejl og fixes

| Fejl | Fix |
|------|-----|
| `sh:ClassConstraintComponent` | En property peger på forkert type. Tjek target-klasse med `brick_describe` |
| `sh:MinCountConstraintComponent` | Påkrævet property mangler (f.eks. mangler `brick:hasPoint` på udstyr der kræver det) |
| `sh:NodeConstraintComponent` | Entitet mangler `rdf:type` eller har forkert type |
| `sh:MaxCountConstraintComponent` | Property angivet for mange gange |
| Forkert klassenavn | Brug `brick_search` for at finde det præcise navn |

## Typiske Brick-model fejl

```ttl
# FORKERT - brick:Building er deprecated i 1.4
bldg:site1 a brick:Building .

# KORREKT - brug RealEstateCore
bldg:site1 a rec:Building .

# FORKERT - forkert namespace for sensor
bldg:temp_sensor a brick:TemperatureSensor .  # Mangler underscore!

# KORREKT
bldg:temp_sensor a brick:Temperature_Sensor .
```
