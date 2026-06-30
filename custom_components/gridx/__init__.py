"""The gridX Energy Management integration."""

import logging
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GridxApi
from .const import (
    CONF_PROVIDER,
    COORDINATOR_HISTORICAL,
    COORDINATOR_LIVE,
    DEFAULT_PROVIDER,
    DOMAIN,
)
from .coordinator import GridxCoordinator, GridxHistoricalCoordinator

_LOGGER = logging.getLogger(__name__)

type GridxConfigEntry = ConfigEntry[dict]

PLATFORMS = ["sensor"]


# ---------------------------------------------------------------------------
# Battery applianceID -> system_id migration
#
# Battery sensors used to be keyed by the gridX applianceID. gridX reassigns
# that ID on every re-registration / EEBUS re-pairing of the battery, which
# orphaned the old entities (-> unavailable) and spawned a fresh duplicate set
# (..._2, ..._3) each time. Battery sensors are now keyed by system_id (stable).
#
# This migration moves the existing entity that carries the LONGEST history (the
# one with the cleanest entity_id, i.e. no trailing _N — that is the original,
# longest-lived one) onto the new system-level unique_id, preserving its
# entity_id and recorder history, and deletes the remaining duplicate "corpse"
# entities. It runs before the sensor platform is set up, so the new system
# sensors bind to the migrated entity instead of creating yet another duplicate.
# ---------------------------------------------------------------------------

_BATTERY_MEASURE_KEYS = (
    "battery_state_of_charge",
    "battery_power",
    "battery_charge",
    "battery_discharge",
    "battery_remaining_charge",
    "battery_capacity",
    "battery_nominal_capacity",
)


def _battery_target_uid(unique_id: str, system_id: str) -> str | None:
    """Map an appliance-keyed battery unique_id to its system-keyed target.

    Returns None for unique_ids that are not appliance-keyed battery sensors
    (e.g. the hist_battery_* sensors or already system-level ones), so the
    caller leaves them untouched. gridX applianceIDs are UUIDs (no underscores),
    so the key is everything after the first underscore.
    """
    if "_" not in unique_id:
        return None
    rest = unique_id.split("_", 1)[1]
    if rest in _BATTERY_MEASURE_KEYS:
        return f"{system_id}_{rest}"
    if rest == "charge_battery_charge_energy":
        return f"{system_id}_battery_charge_energy"
    if rest == "discharge_battery_discharge_energy":
        return f"{system_id}_battery_discharge_energy"
    return None


def _battery_rename_map(data_by_system: dict) -> dict[str, str]:
    """Old -> new unique_id pairs for the batteries currently reported.

    Used as the multi-system fallback (a dead applianceID can't be attributed
    to a specific system from the unique_id alone, so we only re-key the live
    appliances and leave the rest).
    """
    rename: dict[str, str] = {}
    for system_id, data in data_by_system.items():
        for bat in getattr(data, "batteries", []):
            aid = bat.appliance_id
            if not aid:
                continue
            for key in _BATTERY_MEASURE_KEYS:
                rename[f"{aid}_{key}"] = f"{system_id}_{key}"
            rename[f"{aid}_charge_battery_charge_energy"] = (
                f"{system_id}_battery_charge_energy"
            )
            rename[f"{aid}_discharge_battery_discharge_energy"] = (
                f"{system_id}_battery_discharge_energy"
            )
    return rename


def _entity_id_suffix_rank(entity_id: str) -> int:
    """0 for a clean entity_id, else the trailing _N number.

    The original (longest-lived, most history) entity has no numeric suffix;
    duplicates created later carry _2, _3, ... So a lower rank == more history.
    """
    m = re.search(r"_(\d+)$", entity_id)
    return int(m.group(1)) if m else 0


def _plan_battery_migration(
    entities: list[tuple[str, str]], targets_by_uid: dict[str, str]
) -> tuple[list[tuple[str, str]], list[str]]:
    """Decide which battery entities to re-key and which to cull (pure).

    ``entities`` is a list of (entity_id, unique_id). For every group of
    entities that map to the same system-level target unique_id, the survivor is
    the one with the most history (cleanest entity_id); it is re-keyed to the
    target, the rest are culled. Returns (renames, culls) where renames is a
    list of (entity_id, new_unique_id) and culls a list of entity_id.
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    for entity_id, unique_id in entities:
        target = targets_by_uid.get(unique_id)
        if target is None:
            continue
        groups.setdefault(target, []).append((entity_id, unique_id))

    renames: list[tuple[str, str]] = []
    culls: list[str] = []
    for target, members in groups.items():
        survivor = min(
            members,
            key=lambda m: (_entity_id_suffix_rank(m[0]), len(m[0]), m[0]),
        )
        if survivor[1] != target:
            renames.append((survivor[0], target))
        culls.extend(entity_id for entity_id, _ in members if entity_id != survivor[0])
    return renames, culls


def _migrate_battery_entities(hass: HomeAssistant, entry: GridxConfigEntry) -> None:
    """Re-key battery entities to system_id and cull the applianceID corpses."""
    coordinator: GridxCoordinator = entry.runtime_data[COORDINATOR_LIVE]
    ent_reg = er.async_get(hass)
    system_ids = set(coordinator.data)

    battery_entities: list[tuple[str, str]] = []
    targets: dict[str, str] = {}
    single_system = next(iter(system_ids)) if len(system_ids) == 1 else None
    for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if "battery" not in ent.unique_id:
            continue
        battery_entities.append((ent.entity_id, ent.unique_id))
        if single_system is not None:
            target = _battery_target_uid(ent.unique_id, single_system)
            if target and target != ent.unique_id:
                targets[ent.unique_id] = target
    if single_system is None:
        targets = _battery_rename_map(coordinator.data)

    renames, culls = _plan_battery_migration(battery_entities, targets)
    if not renames and not culls:
        return

    for entity_id in culls:
        ent_reg.async_remove(entity_id)
    for entity_id, new_uid in renames:
        if ent_reg.async_get_entity_id("sensor", DOMAIN, new_uid) is None:
            ent_reg.async_update_entity(entity_id, new_unique_id=new_uid)

    # Remove gridX devices left empty by the cull (the dead battery devices).
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if not er.async_entries_for_device(
            ent_reg, device.id, include_disabled_entities=True
        ):
            dev_reg.async_remove_device(device.id)

    _LOGGER.info(
        "gridX battery migration: re-keyed %d entit%s to system-level, "
        "culled %d applianceID corpse%s",
        len(renames),
        "y" if len(renames) == 1 else "ies",
        len(culls),
        "" if len(culls) == 1 else "s",
    )


async def async_setup_entry(hass: HomeAssistant, entry: GridxConfigEntry) -> bool:
    """Set up gridX from a config entry."""
    api = GridxApi(
        async_get_clientsession(hass),
        entry.data["email"],
        entry.data["password"],
        provider=entry.data.get(CONF_PROVIDER, DEFAULT_PROVIDER),
    )
    live_coordinator = GridxCoordinator(hass, api, entry)
    historical_coordinator = GridxHistoricalCoordinator(hass, api, entry)
    await live_coordinator.async_config_entry_first_refresh()
    try:
        await historical_coordinator.async_config_entry_first_refresh()
    except Exception:
        _LOGGER.warning("Historical data unavailable, historical sensors will be empty")

    entry.runtime_data = {
        COORDINATOR_LIVE: live_coordinator,
        COORDINATOR_HISTORICAL: historical_coordinator,
    }
    # Migrate appliance-keyed battery entities to stable system-level keys
    # before the sensor platform creates the (new) system battery sensors.
    _migrate_battery_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GridxConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
