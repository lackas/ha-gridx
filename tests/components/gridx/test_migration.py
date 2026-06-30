"""Tests for the battery applianceID -> system_id migration planner."""

from custom_components.gridx import (
    _battery_rename_map,
    _battery_target_uid,
    _entity_id_suffix_rank,
    _plan_battery_migration,
)
from custom_components.gridx.models import GridxBattery, GridxSystemData

# Real-looking UUIDs (no underscores, like gridX applianceIDs).
OLD = "f0520e5a-66b5-4de5-aaae-b0487314b9ae"  # original, most history
MID = "59538119-1f51-4642-9093-dd71cdabadfb"  # intermediate
LIVE = "26b691d5-6c69-4911-b287-501b42240785"  # current live
SYS = "72885640-0fb1-4cba-92a6-d2cd83cbc7b5"


class TestTargetUid:
    def test_measurement_keys_map_to_system(self):
        assert (
            _battery_target_uid(f"{LIVE}_battery_state_of_charge", SYS)
            == f"{SYS}_battery_state_of_charge"
        )
        assert (
            _battery_target_uid(f"{OLD}_battery_nominal_capacity", SYS)
            == f"{SYS}_battery_nominal_capacity"
        )

    def test_energy_infix_keys_map_to_system(self):
        assert (
            _battery_target_uid(f"{LIVE}_charge_battery_charge_energy", SYS)
            == f"{SYS}_battery_charge_energy"
        )
        assert (
            _battery_target_uid(f"{LIVE}_discharge_battery_discharge_energy", SYS)
            == f"{SYS}_battery_discharge_energy"
        )

    def test_non_battery_and_hist_left_untouched(self):
        # historical sensors and unrelated keys are not migration targets
        assert _battery_target_uid(f"{SYS}_hist_battery_charge", SYS) is None
        assert _battery_target_uid(f"{SYS}_grid_import_energy", SYS) is None
        assert _battery_target_uid("no-underscore", SYS) is None


class TestSuffixRank:
    def test_clean_entity_id_ranks_zero(self):
        assert _entity_id_suffix_rank("sensor.gridx_battery_state_of_charge") == 0

    def test_numeric_suffix_ranks_higher(self):
        assert _entity_id_suffix_rank("sensor.gridx_battery_state_of_charge_2") == 2
        assert _entity_id_suffix_rank("sensor.gridx_battery_2_state_of_charge") == 0


class TestPlanBatteryMigration:
    def test_survivor_is_longest_history_rest_culled(self):
        """The clean (no-suffix) entity survives and is re-keyed; rest culled."""
        entities = [
            # dead original, bare entity_id -> most history -> survivor
            ("sensor.gridx_battery_state_of_charge", f"{OLD}_battery_state_of_charge"),
            # current live duplicate
            (
                "sensor.gridx_battery_state_of_charge_2",
                f"{LIVE}_battery_state_of_charge",
            ),
            # intermediate, different device-name pattern
            (
                "sensor.gridx_battery_2_state_of_charge",
                f"{MID}_battery_state_of_charge",
            ),
        ]
        targets = {uid: f"{SYS}_battery_state_of_charge" for _, uid in entities}

        renames, culls = _plan_battery_migration(entities, targets)

        assert renames == [
            ("sensor.gridx_battery_state_of_charge", f"{SYS}_battery_state_of_charge")
        ]
        assert set(culls) == {
            "sensor.gridx_battery_state_of_charge_2",
            "sensor.gridx_battery_2_state_of_charge",
        }

    def test_energy_sensor_migrates_with_infix(self):
        entities = [
            (
                "sensor.gridx_battery_charge_energy",
                f"{OLD}_charge_battery_charge_energy",
            ),
            (
                "sensor.gridx_battery_charge_energy_2",
                f"{LIVE}_charge_battery_charge_energy",
            ),
        ]
        targets = {uid: f"{SYS}_battery_charge_energy" for _, uid in entities}

        renames, culls = _plan_battery_migration(entities, targets)

        assert renames == [
            ("sensor.gridx_battery_charge_energy", f"{SYS}_battery_charge_energy")
        ]
        assert culls == ["sensor.gridx_battery_charge_energy_2"]

    def test_already_system_level_is_noop(self):
        """When the survivor already holds the target uid, nothing is re-keyed."""
        entities = [
            (
                "sensor.gridx_battery_state_of_charge",
                f"{SYS}_battery_state_of_charge",
            ),
        ]
        targets = {f"{SYS}_battery_state_of_charge": f"{SYS}_battery_state_of_charge"}

        renames, culls = _plan_battery_migration(entities, targets)

        assert renames == []
        assert culls == []

    def test_unmapped_entities_ignored(self):
        """Entities without a target (hist_, system-level) are left alone."""
        entities = [
            ("sensor.gridx_battery_charge_today", f"{SYS}_hist_battery_charge"),
        ]
        renames, culls = _plan_battery_migration(entities, {})
        assert renames == []
        assert culls == []


class TestRenameMap:
    def test_rename_map_covers_all_keys(self):
        data = GridxSystemData(batteries=[GridxBattery(appliance_id=LIVE)])
        rename = _battery_rename_map({SYS: data})

        assert rename[f"{LIVE}_battery_state_of_charge"] == (
            f"{SYS}_battery_state_of_charge"
        )
        assert rename[f"{LIVE}_charge_battery_charge_energy"] == (
            f"{SYS}_battery_charge_energy"
        )
        assert rename[f"{LIVE}_discharge_battery_discharge_energy"] == (
            f"{SYS}_battery_discharge_energy"
        )
        # 7 measurement + 2 energy = 9 mappings per battery
        assert len(rename) == 9

    def test_empty_appliance_id_skipped(self):
        data = GridxSystemData(batteries=[GridxBattery(appliance_id="")])
        assert _battery_rename_map({SYS: data}) == {}
