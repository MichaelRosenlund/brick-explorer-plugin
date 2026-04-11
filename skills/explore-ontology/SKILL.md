---
name: explore-ontology
description: Explore the Brick building ontology - search for classes, view class hierarchies, and get detailed descriptions of Brick concepts (Equipment, Points, Locations, etc.). Use when the user asks about Brick classes, what types of equipment or sensors exist in Brick, or needs to understand the ontology structure.
---

# Udforsk Brick-ontologien

Brug MCP-toolsene `brick_search`, `brick_hierarchy` og `brick_describe` til at navigere Brick-ontologien.

## Workflow

1. **Søg** med `brick_search` når brugeren angiver et nøgleord (f.eks. "temperature", "AHU", "pump")
2. **Beskriv** med `brick_describe` for at se fuld info om en specifik klasse
3. **Hierarki** med `brick_hierarchy` for at se forældre- eller børneklasser

## Brick's 7 top-level klasser

- **Equipment** – Fysiske enheder (HVAC, el-udstyr, pumper, ventiler, etc.)
- **Point** – Datapunkter (Sensor, Setpoint, Command, Status, Alarm, Parameter)
- **Collection** – Logiske grupperinger (System, Loop, Portfolio)
- **Location** – Fysiske rum/steder *(deprecated i 1.4 – brug RealEstateCore)*
- **Quantity** – Målestørrelser (Temperature, Pressure, Humidity, etc.)
- **Substance** – Stoffer/medier (Supply_Water, Return_Air, etc.)
- **Tag** – Klassifikations-tags (bruges til Haystack-mapping)

## Vigtige navnekonventioner

- Brick-klasser bruger underscore: `Air_Handling_Unit`, ikke `AirHandlingUnit`
- Mange klasser har aliaser via `owl:equivalentClass` (f.eks. `AHU` = `Air_Handling_Unit`)
- Brug `brick_describe` for at se aliaser og deprecation-info

## Brick 1.4 ændringer

- `brick:Location`-klasser (Building, Floor, Room) er deprecated
- Brug tilsvarende RealEstateCore-klasser: `rec:Building`, `rec:Level`, `rec:Room`
- Equipment- og Point-klasser er uændrede i brick:-namespace

## Eksempler

```
brick_search("chiller")         → alle chiller-relaterede klasser
brick_hierarchy("Sensor", depth=2)  → sensor-hierarki 2 niveauer ned
brick_describe("Air_Handling_Unit") → fuld beskrivelse af AHU
brick_hierarchy("Temperature_Sensor", direction="ancestors") → forfædreklasser
```
