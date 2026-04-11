---
name: create-model
description: Generate Brick building model .ttl files. Use when the user wants to create a new Brick model for a building, add equipment/sensors/locations to an existing model, or needs help structuring building data with Brick classes and relationships.
---

# Opret Brick bygningsmodeller

Brug `brick_generate_model`, `brick_search`, `brick_describe` og `brick_validate_ttl` til at oprette valide Brick-modeller.

## Workflow

1. **Indsaml bygningsinfo** – spørg om:
   - Udstyr (AHUs, VAV-bokse, chillere, pumper, etc.)
   - Sensorer og setpoints på hvert udstyr
   - Rum/lokationer (etager, rum, zoner)
   - Forbindelser (hvad feeder hvad?)

2. **Find korrekte Brick-klasser** med `brick_search` og `brick_describe`
   - Prefer specifikke subklasser over generelle (f.eks. `Supply_Air_Temperature_Sensor` > `Temperature_Sensor`)

3. **Generer modellen** med `brick_generate_model`

4. **Valider** med `brick_validate_ttl` (tager 20-30 sek)

5. **Gem** den validerede TTL til en fil

## Entitets-format til brick_generate_model

```python
entities = [
    # Lokation
    {"id": "floor_1", "type": "rec:Level", "label": "Etage 1"},

    # Udstyr med points og lokation
    {
        "id": "ahu_1",
        "type": "Air_Handling_Unit",
        "label": "AHU 1",
        "hasLocation": "floor_1",
        "hasPoint": ["sat_sensor_ahu1", "rat_sensor_ahu1", "supply_flow_sp_ahu1"],
        "feeds": ["vav_1", "vav_2"]
    },

    # Sensor
    {"id": "sat_sensor_ahu1", "type": "Supply_Air_Temperature_Sensor", "label": "SAT Sensor AHU 1"},
    {"id": "rat_sensor_ahu1", "type": "Return_Air_Temperature_Sensor", "label": "RAT Sensor AHU 1"},
    {"id": "supply_flow_sp_ahu1", "type": "Supply_Air_Flow_Setpoint", "label": "Supply Air Flow SP AHU 1"},

    # VAV-boks
    {
        "id": "vav_1",
        "type": "Variable_Air_Volume_Box",
        "label": "VAV 1",
        "hasPoint": ["vav1_flow_sensor", "vav1_damper_pos"]
    },
]
```

## Vigtige modelleringsregler

| Regel | Beskrivelse |
|-------|-------------|
| `rdf:type` | Alle entiteter skal have en Brick-type |
| `brick:hasPoint` | Udstyr → Point (sensorer, setpoints, kommandoer) |
| `brick:feeds` | Udstyr → Udstyr (luft/vand-flow) |
| `brick:hasLocation` | Udstyr/Point → Lokation |
| `brick:hasPart` | Udstyr → Sub-udstyr (f.eks. AHU → Fan) |
| `brick:isPartOf` | Invers af hasPart |

## Brick 1.4: Location-klasser

```ttl
# Deprecated (brug ikke):
bldg:rum_101 a brick:Room .
bldg:etage_1 a brick:Floor .
bldg:bygning a brick:Building .

# Korrekt i Brick 1.4 (RealEstateCore):
bldg:rum_101 a rec:Room .
bldg:etage_1 a rec:Level .
bldg:bygning a rec:Building .
```

## Navnekonventioner

- Instans-ID'er: `snake_case`, f.eks. `ahu_1`, `floor_1_vav_3`
- Undgå specialtegn (brug `_` eller `-`)
- Vær konsistent: `sat` = Supply Air Temperature, `rat` = Return Air Temperature
