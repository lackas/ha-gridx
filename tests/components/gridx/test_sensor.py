"""Tests for gridX sensor platform."""

import pytest

from custom_components.gridx.models import (
    GridxBattery,
    GridxEVChargingStation,
    GridxHeater,
    GridxHeatPump,
    GridxSystemData,
)


# ---------------------------------------------------------------------------
# Helpers — imported from sensor module after it exists
# ---------------------------------------------------------------------------


def _get_descriptions():
    from custom_components.gridx.sensor import (
        BATTERY_SENSOR_DESCRIPTIONS,
        EV_CHARGER_SENSOR_DESCRIPTIONS,
        HEATER_SENSOR_DESCRIPTIONS,
        HEAT_PUMP_SENSOR_DESCRIPTIONS,
        SYSTEM_SENSOR_DESCRIPTIONS,
    )

    return (
        SYSTEM_SENSOR_DESCRIPTIONS,
        BATTERY_SENSOR_DESCRIPTIONS,
        HEAT_PUMP_SENSOR_DESCRIPTIONS,
        EV_CHARGER_SENSOR_DESCRIPTIONS,
        HEATER_SENSOR_DESCRIPTIONS,
    )


def _get_historical_descriptions():
    from custom_components.gridx.sensor import HISTORICAL_SYSTEM_SENSOR_DESCRIPTIONS

    return HISTORICAL_SYSTEM_SENSOR_DESCRIPTIONS


def _get_appliance_name(base_name: str, index: int, total: int) -> str:
    """Replicate sensor naming logic for tests."""
    from custom_components.gridx.sensor import _appliance_device_name

    return _appliance_device_name(base_name, index, total)


# ---------------------------------------------------------------------------
# System sensor value extraction
# ---------------------------------------------------------------------------


class TestSystemSensorValueExtraction:
    def test_system_sensor_value_extraction(self):
        """All SYSTEM_SENSOR_DESCRIPTIONS value_fns return the correct field."""
        data = GridxSystemData(
            production=100.0,
            photovoltaic=200.0,
            consumption=300.0,
            total_consumption=400.0,
            grid=50.0,
            self_consumption=120.0,
            self_supply=130.0,
            self_consumption_rate=0.75,
            self_sufficiency_rate=0.80,
            direct_consumption_household=60.0,
            direct_consumption_heat_pump=70.0,
            direct_consumption_ev=80.0,
            direct_consumption_heater=90.0,
            direct_consumption_rate=0.50,
            heat_pump=110.0,
            grid_meter_reading_negative=5000.0,
            grid_meter_reading_positive=9000.0,
        )

        (
            SYSTEM_SENSOR_DESCRIPTIONS,
            _,
            _,
            _,
            _,
        ) = _get_descriptions()

        desc_map = {d.key: d for d in SYSTEM_SENSOR_DESCRIPTIONS}

        assert desc_map["production"].value_fn(data) == pytest.approx(100.0)
        assert desc_map["photovoltaic"].value_fn(data) == pytest.approx(200.0)
        assert desc_map["consumption"].value_fn(data) == pytest.approx(300.0)
        assert desc_map["total_consumption"].value_fn(data) == pytest.approx(400.0)
        assert desc_map["grid"].value_fn(data) == pytest.approx(50.0)
        assert desc_map["self_consumption"].value_fn(data) == pytest.approx(120.0)
        assert desc_map["self_supply"].value_fn(data) == pytest.approx(130.0)
        assert desc_map["direct_consumption_household"].value_fn(data) == pytest.approx(
            60.0
        )
        assert desc_map["direct_consumption_heat_pump"].value_fn(data) == pytest.approx(
            70.0
        )
        assert desc_map["direct_consumption_ev"].value_fn(data) == pytest.approx(80.0)
        assert desc_map["direct_consumption_heater"].value_fn(data) == pytest.approx(
            90.0
        )
        assert desc_map["heat_pump"].value_fn(data) == pytest.approx(110.0)
        # API returns Ws, value_fn converts to Wh (÷ 3600)
        assert desc_map["grid_meter_reading_negative"].value_fn(data) == pytest.approx(
            5000.0 / 3600
        )
        assert desc_map["grid_meter_reading_positive"].value_fn(data) == pytest.approx(
            9000.0 / 3600
        )

    def test_rate_sensors_multiply_by_100(self):
        """Rate sensors (0–1 floats) are multiplied by 100 before returning."""
        data = GridxSystemData(
            self_consumption_rate=0.88,
            self_sufficiency_rate=0.97,
            direct_consumption_rate=0.55,
        )

        (SYSTEM_SENSOR_DESCRIPTIONS, _, _, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in SYSTEM_SENSOR_DESCRIPTIONS}

        assert desc_map["self_consumption_rate"].value_fn(data) == pytest.approx(88.0)
        assert desc_map["self_sufficiency_rate"].value_fn(data) == pytest.approx(97.0)
        assert desc_map["direct_consumption_rate"].value_fn(data) == pytest.approx(55.0)

    def test_system_descriptions_count(self):
        """There are exactly 17 system sensor descriptions."""
        (SYSTEM_SENSOR_DESCRIPTIONS, _, _, _, _) = _get_descriptions()
        assert len(SYSTEM_SENSOR_DESCRIPTIONS) == 17


# ---------------------------------------------------------------------------
# Battery sensor value extraction
# ---------------------------------------------------------------------------


class TestBatterySensorValueExtraction:
    def test_battery_sensor_value_extraction(self):
        """All BATTERY_SENSOR_DESCRIPTIONS value_fns return correct fields."""
        battery = GridxBattery(
            appliance_id="bat-1",
            state_of_charge=0.75,
            power=1000.0,
            charge=200.0,
            discharge=0.0,
            remaining_charge=11000.0,
            capacity=15000.0,
            nominal_capacity=15000.0,
        )

        (_, BATTERY_SENSOR_DESCRIPTIONS, _, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in BATTERY_SENSOR_DESCRIPTIONS}

        # state_of_charge is multiplied by 100
        assert desc_map["battery_state_of_charge"].value_fn(battery) == pytest.approx(
            75.0
        )
        assert desc_map["battery_power"].value_fn(battery) == pytest.approx(1000.0)
        assert desc_map["battery_charge"].value_fn(battery) == pytest.approx(200.0)
        assert desc_map["battery_discharge"].value_fn(battery) == pytest.approx(0.0)
        assert desc_map["battery_remaining_charge"].value_fn(battery) == pytest.approx(
            11000.0
        )
        assert desc_map["battery_capacity"].value_fn(battery) == pytest.approx(15000.0)
        assert desc_map["battery_nominal_capacity"].value_fn(battery) == pytest.approx(
            15000.0
        )

    def test_battery_descriptions_count(self):
        """There are exactly 7 battery sensor descriptions."""
        (_, BATTERY_SENSOR_DESCRIPTIONS, _, _, _) = _get_descriptions()
        assert len(BATTERY_SENSOR_DESCRIPTIONS) == 7


# ---------------------------------------------------------------------------
# Heat pump sensor value extraction
# ---------------------------------------------------------------------------


class TestHeatPumpSensorValueExtraction:
    def test_heat_pump_sg_ready_state(self):
        """sg_ready_state value_fn returns known states, None for unknown."""
        (_, _, HEAT_PUMP_SENSOR_DESCRIPTIONS, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in HEAT_PUMP_SENSOR_DESCRIPTIONS}
        sg_fn = desc_map["heat_pump_sg_ready_state"].value_fn

        # Known states pass through
        for state in ["UNKNOWN", "OFF", "AUTO", "RECOMMEND_ON", "ON"]:
            hp = GridxHeatPump(appliance_id="hp-1", power=500.0, sg_ready_state=state)
            assert sg_fn(hp) == state

        # Unknown state returns None (avoids entity becoming unavailable)
        hp = GridxHeatPump(
            appliance_id="hp-1", power=500.0, sg_ready_state="FUTURE_STATE"
        )
        assert sg_fn(hp) is None

        # Power still works
        hp = GridxHeatPump(appliance_id="hp-1", power=500.0, sg_ready_state="AUTO")
        assert desc_map["heat_pump_power"].value_fn(hp) == pytest.approx(500.0)

    def test_heat_pump_descriptions_count(self):
        """There are exactly 2 heat pump sensor descriptions."""
        (_, _, HEAT_PUMP_SENSOR_DESCRIPTIONS, _, _) = _get_descriptions()
        assert len(HEAT_PUMP_SENSOR_DESCRIPTIONS) == 2


# ---------------------------------------------------------------------------
# EV charger sensor value extraction
# ---------------------------------------------------------------------------


class TestEVChargerSensorValueExtraction:
    def test_ev_charger_sensor_value_extraction(self):
        """All EV_CHARGER_SENSOR_DESCRIPTIONS value_fns return correct fields."""
        ev = GridxEVChargingStation(
            appliance_id="ev-1",
            power=7000.0,
            state_of_charge=0.45,
            current_l1=10.5,
            current_l2=10.3,
            current_l3=10.4,
            reading_total=123.456,
        )

        (_, _, _, EV_CHARGER_SENSOR_DESCRIPTIONS, _) = _get_descriptions()
        desc_map = {d.key: d for d in EV_CHARGER_SENSOR_DESCRIPTIONS}

        assert desc_map["ev_charger_power"].value_fn(ev) == pytest.approx(7000.0)
        # state_of_charge is multiplied by 100
        assert desc_map["ev_charger_state_of_charge"].value_fn(ev) == pytest.approx(
            45.0
        )
        assert desc_map["ev_charger_current_l1"].value_fn(ev) == pytest.approx(10.5)
        assert desc_map["ev_charger_current_l2"].value_fn(ev) == pytest.approx(10.3)
        assert desc_map["ev_charger_current_l3"].value_fn(ev) == pytest.approx(10.4)
        assert desc_map["ev_charger_reading_total"].value_fn(ev) == pytest.approx(
            123.456
        )

    def test_ev_charger_descriptions_count(self):
        """There are exactly 6 EV charger sensor descriptions."""
        (_, _, _, EV_CHARGER_SENSOR_DESCRIPTIONS, _) = _get_descriptions()
        assert len(EV_CHARGER_SENSOR_DESCRIPTIONS) == 6


# ---------------------------------------------------------------------------
# Heater sensor value extraction
# ---------------------------------------------------------------------------


class TestHeaterSensorValueExtraction:
    def test_heater_sensor_value_extraction(self):
        """All HEATER_SENSOR_DESCRIPTIONS value_fns return correct fields."""
        heater = GridxHeater(appliance_id="heater-1", power=2000.0, temperature=65.5)

        (_, _, _, _, HEATER_SENSOR_DESCRIPTIONS) = _get_descriptions()
        desc_map = {d.key: d for d in HEATER_SENSOR_DESCRIPTIONS}

        assert desc_map["heater_power"].value_fn(heater) == pytest.approx(2000.0)
        assert desc_map["heater_temperature"].value_fn(heater) == pytest.approx(65.5)

    def test_heater_descriptions_count(self):
        """There are exactly 2 heater sensor descriptions."""
        (_, _, _, _, HEATER_SENSOR_DESCRIPTIONS) = _get_descriptions()
        assert len(HEATER_SENSOR_DESCRIPTIONS) == 2


# ---------------------------------------------------------------------------
# Appliance naming
# ---------------------------------------------------------------------------


class TestApplianceNaming:
    def test_appliance_naming_single(self):
        """With 1 appliance, device name has no suffix."""
        assert _get_appliance_name("Battery", 0, 1) == "Battery"
        assert _get_appliance_name("Heat Pump", 0, 1) == "Heat Pump"
        assert _get_appliance_name("EV Charger", 0, 1) == "EV Charger"
        assert _get_appliance_name("Heater", 0, 1) == "Heater"

    def test_appliance_naming_multiple(self):
        """With 2+ appliances, second+ get numeric suffix starting at 2."""
        assert _get_appliance_name("Battery", 0, 2) == "Battery"
        assert _get_appliance_name("Battery", 1, 2) == "Battery 2"
        assert _get_appliance_name("Battery", 2, 3) == "Battery 3"

    def test_appliance_naming_three(self):
        """Third appliance gets suffix 3."""
        assert _get_appliance_name("Heat Pump", 0, 3) == "Heat Pump"
        assert _get_appliance_name("Heat Pump", 1, 3) == "Heat Pump 2"
        assert _get_appliance_name("Heat Pump", 2, 3) == "Heat Pump 3"


# ---------------------------------------------------------------------------
# Diagnostic entity categories
# ---------------------------------------------------------------------------


class TestDiagnosticEntities:
    def test_diagnostic_entities_have_category(self):
        """Battery capacity and nominal_capacity must have entity_category=DIAGNOSTIC."""
        from homeassistant.const import EntityCategory

        (_, BATTERY_SENSOR_DESCRIPTIONS, _, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in BATTERY_SENSOR_DESCRIPTIONS}

        assert desc_map["battery_capacity"].entity_category == EntityCategory.DIAGNOSTIC
        assert (
            desc_map["battery_nominal_capacity"].entity_category
            == EntityCategory.DIAGNOSTIC
        )

    def test_non_diagnostic_battery_sensors(self):
        """power, charge, discharge etc. must NOT have DIAGNOSTIC category."""
        from homeassistant.const import EntityCategory

        (_, BATTERY_SENSOR_DESCRIPTIONS, _, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in BATTERY_SENSOR_DESCRIPTIONS}

        for key in (
            "battery_state_of_charge",
            "battery_power",
            "battery_charge",
            "battery_discharge",
            "battery_remaining_charge",
        ):
            assert desc_map[key].entity_category != EntityCategory.DIAGNOSTIC, (
                f"{key} should not be DIAGNOSTIC"
            )


# ---------------------------------------------------------------------------
# No appliances → no appliance entities
# ---------------------------------------------------------------------------


class TestNoAppliances:
    def test_no_appliances_no_entities(self):
        """With all empty appliance lists, only system sensors are created."""
        from unittest.mock import MagicMock

        from custom_components.gridx.sensor import _build_entities

        coordinator = MagicMock()
        coordinator.data = {
            "system-1": GridxSystemData()  # all appliance lists empty
        }

        entities = _build_entities(coordinator)

        from custom_components.gridx.sensor import (
            GridxSystemSensor,
            GridxSystemEnergySensor,
        )

        system_entities = [
            e
            for e in entities
            if isinstance(e, (GridxSystemSensor, GridxSystemEnergySensor))
        ]
        appliance_entities = [
            e
            for e in entities
            if not isinstance(e, (GridxSystemSensor, GridxSystemEnergySensor))
        ]

        assert len(system_entities) == 17 + 8  # 17 power/rate + 8 energy accumulators
        assert len(appliance_entities) == 0

    def test_with_appliances_creates_entities(self):
        """With 1 battery + 1 heat pump, correct number of entities are created."""
        from unittest.mock import MagicMock

        from custom_components.gridx.sensor import (
            GridxApplianceEnergySensor,
            GridxApplianceSensor,
            GridxSystemSensor,
            _build_entities,
        )

        data = GridxSystemData(
            batteries=[GridxBattery(appliance_id="bat-1")],
            heat_pumps=[GridxHeatPump(appliance_id="hp-1", sg_ready_state="AUTO")],
        )

        coordinator = MagicMock()
        coordinator.data = {"system-1": data}

        entities = _build_entities(coordinator)

        system_count = sum(1 for e in entities if isinstance(e, GridxSystemSensor))
        appliance_count = sum(
            1 for e in entities if isinstance(e, GridxApplianceSensor)
        )
        energy_count = sum(
            1 for e in entities if isinstance(e, GridxApplianceEnergySensor)
        )

        assert system_count == 17
        # 7 battery + 2 heat pump = 9 appliance sensors
        assert appliance_count == 9
        # 1 heat pump energy + 2 battery energy (charge + discharge) = 3
        assert energy_count == 3


# ---------------------------------------------------------------------------
# Energy sensor class attributes
# ---------------------------------------------------------------------------


class TestEnergySensor:
    def test_energy_sensor_uses_restore_sensor(self):
        """Energy sensor must inherit from RestoreSensor for state restoration."""
        from homeassistant.components.sensor import RestoreSensor

        from custom_components.gridx.sensor import GridxApplianceEnergySensor

        assert issubclass(GridxApplianceEnergySensor, RestoreSensor)

    def test_energy_sensor_created_for_heat_pump(self):
        """Each heat pump gets an energy accumulator sensor."""
        from unittest.mock import MagicMock

        from custom_components.gridx.sensor import (
            GridxApplianceEnergySensor,
            _build_entities,
        )

        data = GridxSystemData(
            heat_pumps=[
                GridxHeatPump(appliance_id="hp-1", sg_ready_state="AUTO"),
                GridxHeatPump(appliance_id="hp-2", sg_ready_state="OFF"),
            ],
        )
        coordinator = MagicMock()
        coordinator.data = {"sys-1": data}

        entities = _build_entities(coordinator)
        energy_entities = [
            e for e in entities if isinstance(e, GridxApplianceEnergySensor)
        ]

        assert len(energy_entities) == 2
        unique_ids = {e._attr_unique_id for e in energy_entities}
        assert unique_ids == {"hp-1_heat_pump_energy", "hp-2_heat_pump_energy"}


# ---------------------------------------------------------------------------
# direct_consumption_rate visibility
# ---------------------------------------------------------------------------


class TestSensorVisibility:
    def test_direct_consumption_rate_hidden_by_default(self):
        """direct_consumption_rate should be hidden in entity registry by default."""
        (SYSTEM_SENSOR_DESCRIPTIONS, _, _, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in SYSTEM_SENSOR_DESCRIPTIONS}

        assert (
            desc_map["direct_consumption_rate"].entity_registry_visible_default is False
        )

    def test_other_system_sensors_visible_by_default(self):
        """Most system sensors should be visible by default (None = True)."""
        (SYSTEM_SENSOR_DESCRIPTIONS, _, _, _, _) = _get_descriptions()
        desc_map = {d.key: d for d in SYSTEM_SENSOR_DESCRIPTIONS}

        # Spot-check a few that should be visible
        for key in ("production", "consumption", "grid", "self_consumption_rate"):
            val = desc_map[key].entity_registry_visible_default
            assert val is not False, f"{key} should be visible by default"


class TestHistoricalSystemSensors:
    def test_historical_descriptions_extract_expected_values(self):
        """Historical descriptions read the expected total values."""
        descriptions = _get_historical_descriptions()
        desc_map = {d.key: d for d in descriptions}
        data = {
            "battery": {"charge": 4820.0, "discharge": 4175.0},
            "heatPump": 9630.0,
            "directConsumptionHeatPump": 2310.0,
        }

        assert desc_map["hist_battery_charge"].value_fn(data) == pytest.approx(4820.0)
        assert desc_map["hist_battery_discharge"].value_fn(data) == pytest.approx(
            4175.0
        )
        assert desc_map["hist_heat_pump_energy"].value_fn(data) == pytest.approx(9630.0)
        assert desc_map["hist_direct_consumption_heat_pump"].value_fn(
            data
        ) == pytest.approx(2310.0)

    def test_historical_descriptions_disabled_by_default(self):
        """Historical sensors must be disabled by default."""
        descriptions = _get_historical_descriptions()

        assert len(descriptions) == 4
        for description in descriptions:
            assert description.entity_registry_enabled_default is False

    def test_build_historical_entities(self):
        """Historical coordinator data creates four system entities per system."""
        from unittest.mock import MagicMock

        from custom_components.gridx.sensor import (
            GridxHistoricalSystemSensor,
            _build_historical_entities,
        )

        coordinator = MagicMock()
        coordinator.data = {
            "system-1": {
                "battery": {"charge": 4820.0, "discharge": 4175.0},
                "heatPump": 9630.0,
                "directConsumptionHeatPump": 2310.0,
            }
        }

        entities = _build_historical_entities(coordinator)

        assert len(entities) == 4
        assert all(
            isinstance(entity, GridxHistoricalSystemSensor) for entity in entities
        )
        unique_ids = {entity._attr_unique_id for entity in entities}
        assert unique_ids == {
            "system-1_hist_battery_charge",
            "system-1_hist_battery_discharge",
            "system-1_hist_heat_pump_energy",
            "system-1_hist_direct_consumption_heat_pump",
        }
