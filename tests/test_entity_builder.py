"""Dynamic entity editing, scenario persistence, and runtime construction."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import apogee
import pytest
from PySide6.QtWidgets import QApplication

from parameter_window import ParameterWindow
from scenario import (
    ENTITY_TYPES, create_params_from_text, decode_scenario_definition,
    default_parameter_values, encode_scenario,
)


@pytest.fixture
def builder():
    app = QApplication.instance() or QApplication([])
    window = ParameterWindow()
    yield window
    window.close()
    app.processEvents()


def test_add_remove_preserves_edits_and_required_entity_types(builder):
    path = "blue_radar.radar.power_dbw"
    builder.entries[path].setText(" 63.00 ")
    assert not builder.remove_entity("blue_radar")
    assert not builder.entity_cards["blue_radar"].remove_button.isEnabled()

    builder.add_entity_type.setCurrentText("radar")
    builder.add_entity_button.click()
    key = next(key for key in builder.entity_cards if key.startswith("radar_"))
    assert builder.entries[path].text() == " 63.00 "
    assert builder.entity_cards[key].toggle.isChecked()
    assert not builder.entity_cards[key].body.isHidden()
    builder.entity_cards[key].toggle.click()
    assert builder.entity_cards[key].body.isHidden()
    assert builder.entity_cards["blue_radar"].remove_button.isEnabled()
    assert builder.remove_entity(key)
    assert len(builder.params.entities) == 4
    assert not builder.entity_cards["blue_radar"].remove_button.isEnabled()
    assert builder.entries[path].text() == " 63.00 "


def test_team_and_type_are_independent_and_each_entity_has_its_own_parameters(builder):
    key = builder.add_entity("radar")
    card = builder.entity_cards[key]
    card.team_combo.setCurrentText("red")
    card.name_entry.setText("Red search radar")
    assert builder.params.entity(key).team == "red"
    assert builder.params.entity(key).type == "radar"
    assert builder.params.entity(key).display_name == "Red search radar"
    builder.entries[f"{key}.radar.power_dbw"].setText("75")
    params = create_params_from_text(builder._entry_values(), builder.params)
    assert params.entity(key).radar.power_dbw == 75
    assert params.entity("blue_radar").radar.power_dbw == 50

    builder.entity_cards[key].type_combo.setCurrentText("satellite")
    assert builder.params.entity(key).type == "satellite"
    assert builder.params.entity(key).team == "red"
    assert builder.params.entity(key).display_name == "Red search radar"
    assert f"{key}.satellite.orbital_altitude_m" in builder.entries
    assert f"{key}.radar.power_dbw" not in builder.entries
    builder.entity_cards["blue_radar"].type_combo.setCurrentText("missile")
    assert builder.params.entity("blue_radar").type == "radar"
    assert builder.entity_cards["blue_radar"].type_combo.currentText() == "radar"


def test_only_missiles_and_interceptors_offer_target_selection_with_defaults(builder):
    for entity in builder.params.entities:
        card = builder.entity_cards[entity.key]
        if entity.type in ("missile", "interceptor"):
            preferred = "satellite" if entity.type == "missile" else "missile"
            assert builder.params.entity(card.target_combo.currentData()).type == preferred
        else:
            assert not hasattr(card, "target_combo")

    saved = json.loads(encode_scenario(builder._entry_values(), builder.params))
    for entity in saved["entities"]:
        assert ("target_key" in entity) == (entity["type"] in ("missile", "interceptor"))


@pytest.mark.parametrize("kind,target_type", [("missile", "satellite"), ("interceptor", "missile")])
def test_added_pursuers_default_targets_and_preserve_manual_selection(builder, kind, target_type):
    target = builder.add_entity(target_type)
    pursuer = builder.add_entity(kind)
    combo = builder.entity_cards[pursuer].target_combo
    assert builder.params.entity(combo.currentData()).type == target_type
    assert combo.currentData() != target
    combo.setCurrentIndex(combo.findData(target))

    builder.add_entity("radar")

    assert builder.entity_cards[pursuer].target_combo.currentData() == target
    params, _ = decode_scenario_definition(encode_scenario(builder._entry_values(), builder.params))
    assert params.entity(pursuer).initial_pursuit.target_key == target


def test_dynamic_scene_round_trip_preserves_entities_attributes_targets_and_text(builder):
    satellite = builder.add_entity("satellite")
    missile = builder.add_entity("missile")
    builder.entity_cards[missile].team_combo.setCurrentText("neutral")
    builder.entity_cards[missile].name_entry.setText("Observer")
    combo = builder.entity_cards[missile].target_combo
    combo.setCurrentIndex(combo.findData(satellite))
    builder.entries[f"{satellite}.satellite.orbital_altitude_m"].setText(" 450000.00 ")
    values = builder._entry_values()
    params, restored = decode_scenario_definition(encode_scenario(values, builder.params))
    assert restored == values
    assert len(params.entities) == 6
    assert params.entity(missile).team == "neutral"
    assert params.entity(missile).display_name == "Observer"
    assert params.entity(missile).initial_pursuit.target_key == satellite
    runtime = create_params_from_text(restored, params)
    assert runtime.entity(satellite).satellite.orbital_altitude_m == 450000
    assert builder.remove_entity(satellite)
    assert builder.params.entity(missile).initial_pursuit.target_key == "blue_satellite"


def test_dynamic_scene_load_rebuilds_the_entity_list(builder, monkeypatch, tmp_path):
    key = builder.add_entity("interceptor")
    builder.entity_cards[key].team_combo.setCurrentText("red")
    path = tmp_path / "expanded.json"
    path.write_text(encode_scenario(builder._entry_values(), builder.params), encoding="utf-8")
    assert builder.remove_entity(key)
    monkeypatch.setattr("parameter_window.QFileDialog.getOpenFileName",
                        lambda *args: (str(path), "JSON"))
    builder.load_scenario()
    assert len(builder.entity_cards) == 5
    assert builder.entity_cards[key].team_combo.currentText() == "red"
    assert f"{key}.initial_pursuit.speed_mps" in builder.entries


def test_runtime_accepts_custom_keys_and_extra_entities():
    params = apogee.Params()
    entities = []
    for index, kind in enumerate((*ENTITY_TYPES, "missile"), start=10):
        entities.append(apogee.make_entity_definition(kind, f"object_{index}", index))
    params.entities = entities
    satellite = next(entity.key for entity in entities if entity.type == "satellite")
    missile = next(entity.key for entity in entities if entity.type == "missile")
    for entity in params.entities:
        if entity.initial_pursuit is not None:
            params.entity(entity.key).initial_pursuit.target_key = (
                satellite if entity.type == "missile" else missile
            )
    values = default_parameter_values(params)
    values.update({"simulation.duration_s": "0.1", "object_10.radar.bandwidth_hz": "10000",
                   "object_10.radar.pulse_width_us": "100", "object_10.radar.pri_us": "1000"})
    result = apogee.run_sim(create_params_from_text(values, params))
    assert {entity.key for entity in result.entities} == {entity.key for entity in params.entities}
    assert len(result.entities) == 5
    assert all(entity.key not in {"blue_radar", "red_missile"} for entity in result.entities)


@pytest.mark.parametrize("kind", ENTITY_TYPES)
def test_runtime_requires_at_least_one_entity_of_each_type(kind):
    params = apogee.Params()
    params.entities = [entity for entity in params.entities if entity.type != kind]
    with pytest.raises(ValueError, match=kind):
        apogee.run_sim(params)
