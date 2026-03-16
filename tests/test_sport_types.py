from whoop.sport_types import SportType


def test_sport_type_values():
    assert SportType.SAUNA == 233
    assert SportType.WEIGHTLIFTING == 45
    assert SportType.ICE_BATH == 88
    assert SportType.MEDITATION == 70
    assert SportType.RUNNING == 0
    assert SportType.GENERAL_ACTIVITY == -1


def test_sport_type_is_int():
    assert isinstance(SportType.SAUNA, int)
    assert SportType.SAUNA + 0 == 233


def test_sport_type_unique_values():
    values = [member.value for member in SportType]
    assert len(values) == len(set(values))
