# CNX Smart Villa — Home Assistant Custom Integration

Home Assistant commissioning and device-mapping integration for CNX Smart Villa.

## Purpose

This integration turns Home Assistant into the commissioning surface for Smart Villa hardware. Matter, Zigbee, ESPHome, MQTT, Modbus and other integrations remain owned by Home Assistant. CNX Smart Villa adds a stable logical mapping on top:

```text
physical device
  -> Home Assistant entity
  -> CNX Villa / Zone / Function mapping
  -> Smart Villa OS
  -> guest room control
```

The first slice deliberately works in **local commissioning mode** even before the authenticated Smart Villa OS mapping-sync API exists.

## HACS installation

This package is structured to be published as the standalone public repository:

```text
https://github.com/CNXSmartHome/cnx-smart-villa-ha
```

After that public repository is available:

1. Open **HACS** in Home Assistant.
2. Open the menu (three dots) and choose **Custom repositories**.
3. Add `https://github.com/CNXSmartHome/cnx-smart-villa-ha`.
4. Select category **Integration**.
5. Open **CNX Smart Villa** in HACS and choose **Download**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add Integration -> CNX Smart Villa**.

Minimum supported Home Assistant version for the v0.1.x package is **2026.9.0**.

## Manual installation

Copy:

```text
custom_components/cnx_smart_villa
```

to:

```text
/config/custom_components/cnx_smart_villa
```

Restart Home Assistant, then add **CNX Smart Villa** from **Settings -> Devices & services**.

## Current features (v0.1.0)

- UI-based Config Flow; no YAML setup.
- Admin-only `CNX Smart Villa` sidebar panel.
- Discovers supported HA entities from Matter and any other HA provider.
- Shows HA Area, integration platform, manufacturer/model and availability.
- Maps an entity to display name, Villa, Zone, Function, category, criticality, guest-control flag and installer hardware ID.
- Generates the CNX canonical entity ID: `<domain>.vNN_<zone>_<function>`.
- Can rename the Home Assistant entity when the mapping is saved.
- Stores mappings in Home Assistant `.storage`, keyed by stable HA entity-registry entry ID.
- Backend refuses `guest_controllable=true` unless the entity is a supported controllable domain and criticality is `COMFORT`.
- Optional Smart Villa OS health connection using `/api/health`.
- TH/EN Config Flow translations.

## Security boundary

This panel is **admin-only commissioning tooling**. It is not a guest-control endpoint.

It does not expose Home Assistant tokens, does not unlock doors/gates, and does not make HA the booking/access authority. Smart Villa OS remains the source of truth for guest authorization. A local mapping marked `guest_controllable` is only commissioning metadata until the server-side M10 authorization/sync slice validates and imports it.

## Recommended Matter commissioning flow

1. Add the Matter switch directly to Home Assistant.
2. Confirm every gang/endpoint appears and works locally.
3. Open **CNX Smart Villa** in the HA sidebar.
4. Find the new unmapped entity.
5. Set Villa / Zone / Function / Category / Criticality / Guest Control.
6. Save and apply the canonical entity name.
7. Repeat per gang.

Example MH01-3:

```text
switch.mh01_1 -> switch.v01_br01_ceiling
switch.mh01_2 -> switch.v01_br01_bedside
switch.mh01_3 -> switch.v01_br01_cove
```

## Repository layout

The standalone HACS repository must have this structure at its root:

```text
custom_components/
  cnx_smart_villa/
    __init__.py
    manifest.json
    config_flow.py
    ...
brand/
  icon.png
.github/
  workflows/
    validate.yml
hacs.json
README.md
```

The development source currently lives in the Smart Villa monorepo under `integrations/home-assistant/cnx_smart_villa/`. That subtree is intentionally HACS-repo-ready so it can be mirrored to the standalone public repository without restructuring.

## Next slice

M10.1B will add authenticated HA -> Smart Villa OS sync using a dedicated integration token and idempotent mapping endpoint. The custom integration remains the installer UX; Smart Villa OS remains the authorization/business source of truth.
