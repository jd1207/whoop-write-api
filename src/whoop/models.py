from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Recovery:
    cycle_id: int
    recovery_score: float
    hrv: float
    resting_hr: float
    spo2: float | None
    skin_temp: float | None
    created_at: str

    @classmethod
    def from_api(cls, data: dict) -> Recovery:
        score = data["score"]
        return cls(
            cycle_id=data["cycle_id"],
            recovery_score=score["recovery_score"],
            hrv=score["hrv_rmssd_milli"],
            resting_hr=score["resting_heart_rate"],
            spo2=score.get("spo2_percentage"),
            skin_temp=score.get("skin_temp_celsius"),
            created_at=data["created_at"],
        )


@dataclass
class Sleep:
    id: int
    performance: float
    efficiency: float
    respiratory_rate: float
    light_sleep_ms: int
    deep_sleep_ms: int
    rem_sleep_ms: int
    awake_ms: int
    total_in_bed_ms: int
    created_at: str

    @property
    def total_in_bed_hours(self) -> float:
        return self.total_in_bed_ms / 3_600_000

    @classmethod
    def from_api(cls, data: dict) -> Sleep:
        score = data["score"]
        stages = score["stage_summary"]
        return cls(
            id=data["id"],
            performance=score["sleep_performance_percentage"],
            efficiency=score["sleep_efficiency_percentage"],
            respiratory_rate=score["respiratory_rate"],
            light_sleep_ms=stages["total_light_sleep_time_milli"],
            deep_sleep_ms=stages["total_slow_wave_sleep_time_milli"],
            rem_sleep_ms=stages["total_rem_sleep_time_milli"],
            awake_ms=stages["total_awake_time_milli"],
            total_in_bed_ms=stages["total_in_bed_time_milli"],
            created_at=data["created_at"],
        )


@dataclass
class Workout:
    id: int
    sport_id: int
    strain: float
    avg_hr: float
    max_hr: float
    kilojoules: float
    start: str
    end: str

    @classmethod
    def from_api(cls, data: dict) -> Workout:
        score = data.get("score", {})
        return cls(
            id=data["id"],
            sport_id=data["sport_id"],
            strain=score.get("strain", 0.0),
            avg_hr=score.get("average_heart_rate", 0.0),
            max_hr=score.get("max_heart_rate", 0.0),
            kilojoules=score.get("kilojoule", 0.0),
            start=data["start"],
            end=data["end"],
        )


@dataclass
class Cycle:
    id: int
    strain: float
    avg_hr: float
    start: str
    end: str | None

    @classmethod
    def from_api(cls, data: dict) -> Cycle:
        score = data.get("score", {})
        return cls(
            id=data["id"],
            strain=score.get("strain", 0.0),
            avg_hr=score.get("average_heart_rate", 0.0),
            start=data["start"],
            end=data.get("end"),
        )


@dataclass
class BodyMeasurement:
    height_meter: float
    weight_kilogram: float
    max_heart_rate: int

    @classmethod
    def from_api(cls, data: dict) -> BodyMeasurement:
        return cls(
            height_meter=data["height_meter"],
            weight_kilogram=data["weight_kilogram"],
            max_heart_rate=data["max_heart_rate"],
        )


@dataclass
class ExerciseWrite:
    name: str
    sets: int
    reps: int
    weight: float
    weight_unit: str = "lbs"


@dataclass
class WorkoutWrite:
    sport_id: int
    start: str
    end: str
    exercises: list[ExerciseWrite]

    def to_activity_payload(self) -> dict:
        return {
            "gpsEnabled": False,
            "timezoneOffset": "+0000",
            "sportId": self.sport_id,
            "source": "user",
            "during": {
                "lower": self.start,
                "upper": self.end,
                "bounds": "[)",
            },
        }

    def to_exercises_payload(self) -> list[dict]:
        return [
            {
                "name": ex.name,
                "sets": ex.sets,
                "reps": ex.reps,
                "weight": ex.weight,
                "weight_unit": ex.weight_unit,
            }
            for ex in self.exercises
        ]
