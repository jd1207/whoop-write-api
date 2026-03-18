import pytest
import httpx
from whoop.write import WhoopWriteAPI
from whoop.write_models import Exercise
from whoop.write_exercises import ExerciseCatalog
from whoop.client import WhoopClient

MOCK_CATALOG = {
    "exercises": [
        {
            "exercise_id": "BENCHPRESS_BARBELL",
            "name": "Bench Press - Barbell",
            "equipment": "BARBELL",
            "muscle_groups": ["CHEST"],
            "movement_pattern": "HORIZONTAL_PRESS",
            "exercise_type": "STRENGTH",
            "volume_input_format": "REPS",
            "laterality": "BILATERAL",
            "trackable": True,
            "instructions": ["Lie on the bench..."],
            "image_url": "https://example.com/bench.jpg",
            "video_url": "https://example.com/bench.mp4",
        },
        {
            "exercise_id": "FRONTPLANKELBOW",
            "name": "Front Plank",
            "equipment": "BODY",
            "muscle_groups": ["CORE"],
            "movement_pattern": "OTHER",
            "exercise_type": "STRENGTH",
            "volume_input_format": "TIME",
            "laterality": "BILATERAL",
            "trackable": True,
        },
        {
            "exercise_id": "BACKSQUAT_BARBELL",
            "name": "Back Squat - Barbell",
            "equipment": "BARBELL",
            "muscle_groups": ["LEGS"],
            "movement_pattern": "SQUAT",
            "exercise_type": "STRENGTH",
            "volume_input_format": "WEIGHT",
            "laterality": "BILATERAL",
            "trackable": True,
        },
        {
            "exercise_id": "LATERALRAISE_DUMBBELL",
            "name": "Lateral Shoulder Raise - Dumbbell",
            "equipment": "DUMBBELL",
            "muscle_groups": ["SHOULDERS"],
            "movement_pattern": "OTHER",
            "exercise_type": "STRENGTH",
            "volume_input_format": "WEIGHT",
        },
    ],
    "filter_options": {
        "equipment": [
            {"internal_value": "BARBELL", "translated_value": "BARBELL"},
            {"internal_value": "BODY", "translated_value": "BODYWEIGHT"},
            {"internal_value": "DUMBBELL", "translated_value": "DUMBBELL"},
        ],
        "muscle_groups": [
            {"internal_value": "CHEST", "translated_value": "CHEST"},
            {"internal_value": "CORE", "translated_value": "CORE"},
            {"internal_value": "LEGS", "translated_value": "LEGS"},
            {"internal_value": "SHOULDERS", "translated_value": "SHOULDERS"},
        ],
        "movement_patterns": [
            {"internal_value": "HORIZONTAL_PRESS", "translated_value": "HORIZONTAL PRESS"},
            {"internal_value": "SQUAT", "translated_value": "SQUAT"},
            {"internal_value": "OTHER", "translated_value": "OTHER"},
        ],
    },
}


def test_exercise_from_api():
    ex = Exercise.from_api(MOCK_CATALOG["exercises"][0])
    assert ex.exercise_id == "BENCHPRESS_BARBELL"
    assert ex.name == "Bench Press - Barbell"
    assert ex.equipment == "BARBELL"
    assert ex.muscle_groups == ["CHEST"]
    assert ex.movement_pattern == "HORIZONTAL_PRESS"
    assert ex.volume_input_format == "REPS"
    assert ex.instructions == ["Lie on the bench..."]
    assert ex.image_url == "https://example.com/bench.jpg"
    assert ex.video_url == "https://example.com/bench.mp4"


def test_exercise_from_api_minimal():
    ex = Exercise.from_api(MOCK_CATALOG["exercises"][3])
    assert ex.exercise_id == "LATERALRAISE_DUMBBELL"
    assert ex.instructions is None
    assert ex.image_url is None
    assert ex.trackable is True


def test_catalog_from_api():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)
    assert len(catalog.exercises) == 4
    assert "BARBELL" in catalog.equipment_types
    assert "CHEST" in catalog.muscle_groups
    assert "SQUAT" in catalog.movement_patterns


def test_catalog_find_by_id():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)
    ex = catalog.find_by_id("BENCHPRESS_BARBELL")
    assert ex is not None
    assert ex.name == "Bench Press - Barbell"
    assert catalog.find_by_id("NONEXISTENT") is None


def test_catalog_search():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)

    results = catalog.search("bench")
    assert len(results) == 1
    assert results[0].exercise_id == "BENCHPRESS_BARBELL"

    results = catalog.search("squat")
    assert len(results) == 1
    assert results[0].exercise_id == "BACKSQUAT_BARBELL"

    results = catalog.search("PLANK")
    assert len(results) == 1

    results = catalog.search("nonexistent")
    assert len(results) == 0


def test_catalog_filter_by_equipment():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)
    results = catalog.filter(equipment="BARBELL")
    assert len(results) == 2
    assert all(ex.equipment == "BARBELL" for ex in results)


def test_catalog_filter_by_muscle_group():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)
    results = catalog.filter(muscle_group="CHEST")
    assert len(results) == 1
    assert results[0].exercise_id == "BENCHPRESS_BARBELL"


def test_catalog_filter_by_movement_pattern():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)
    results = catalog.filter(movement_pattern="SQUAT")
    assert len(results) == 1
    assert results[0].exercise_id == "BACKSQUAT_BARBELL"


def test_catalog_filter_combined():
    catalog = ExerciseCatalog.from_api(MOCK_CATALOG)
    results = catalog.filter(equipment="BARBELL", muscle_group="LEGS")
    assert len(results) == 1
    assert results[0].exercise_id == "BACKSQUAT_BARBELL"


@pytest.mark.asyncio
async def test_get_exercises(mock_api, fake_token):
    mock_api.get("/weightlifting-service/v2/exercise").mock(
        return_value=httpx.Response(200, json=MOCK_CATALOG)
    )
    api = WhoopWriteAPI(token=fake_token)
    catalog = await api.get_exercises()
    assert len(catalog.exercises) == 4
    assert isinstance(catalog, ExerciseCatalog)


@pytest.mark.asyncio
async def test_get_exercises_cached(mock_api, fake_token):
    route = mock_api.get("/weightlifting-service/v2/exercise").mock(
        return_value=httpx.Response(200, json=MOCK_CATALOG)
    )
    api = WhoopWriteAPI(token=fake_token)
    await api.get_exercises()
    await api.get_exercises()
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_client_get_exercises(mock_api, fake_token):
    mock_api.get("/weightlifting-service/v2/exercise").mock(
        return_value=httpx.Response(200, json=MOCK_CATALOG)
    )
    client = WhoopClient(token=fake_token)
    catalog = await client.get_exercises()
    assert len(catalog.exercises) == 4
    assert catalog.find_by_id("BENCHPRESS_BARBELL") is not None
