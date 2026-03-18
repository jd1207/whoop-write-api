from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ExerciseWrite:
    name: str
    sets: int
    reps: int
    weight: float
    weight_unit: str = "lbs"
    exercise_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "sets": self.sets,
            "reps": self.reps,
            "weight": self.weight,
            "weight_unit": self.weight_unit,
        }

    def to_detailed_dict(self) -> dict:
        """full whoop exercise format with exercise_id and per-set data"""
        exercise_type = "STRENGTH"
        volume_format = "REPS"
        ex_id = self.exercise_id or self.name.upper().replace(" ", "_")
        sets_list = [
            {"number_of_reps": self.reps, "weight": self.weight}
            for _ in range(self.sets)
        ]
        return {
            "exercise_details": {
                "exercise_id": ex_id,
                "name": self.name,
                "exercise_type": exercise_type,
                "volume_input_format": volume_format,
            },
            "sets": sets_list,
        }


@dataclass
class ExerciseSet:
    reps: int = 0
    weight: float = 0
    time_seconds: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"number_of_reps": self.reps, "weight": self.weight}
        if self.time_seconds is not None:
            d["time_in_seconds"] = self.time_seconds
        return d


@dataclass
class DetailedExercise:
    exercise_id: str
    name: str
    sets: list[ExerciseSet]
    exercise_type: str = "STRENGTH"
    volume_format: str = "REPS"

    def to_dict(self) -> dict:
        return {
            "exercise_details": {
                "exercise_id": self.exercise_id,
                "name": self.name,
                "exercise_type": self.exercise_type,
                "volume_input_format": self.volume_format,
            },
            "sets": [s.to_dict() for s in self.sets],
        }


@dataclass
class WorkoutWrite:
    sport_id: int
    start: str
    end: str
    exercises: list[ExerciseWrite] | None = None

    def to_activity_payload(self, timezone_offset: str = "+0000") -> dict:
        return {
            "gpsEnabled": False,
            "timezoneOffset": timezone_offset,
            "sportId": self.sport_id,
            "source": "user",
            "during": {
                "lower": self.start,
                "upper": self.end,
                "bounds": "[)",
            },
        }

    def to_exercises_payload(self) -> list[dict]:
        if not self.exercises:
            return []
        return [ex.to_dict() for ex in self.exercises]


@dataclass
class SportTypeInfo:
    id: int
    name: str

    @classmethod
    def from_api(cls, data: dict) -> SportTypeInfo:
        return cls(id=data["id"], name=data["name"])


@dataclass
class WorkoutResult:
    activity_id: int | str
    exercises_linked: bool
    error: str | None = None


@dataclass
class ActivityResult:
    id: str
    type: str
    score_type: str
    score_state: str

    @classmethod
    def from_api(cls, data: dict) -> ActivityResult:
        return cls(
            id=data["id"],
            type=data["type"],
            score_type=data["score_type"],
            score_state=data["score_state"],
        )


@dataclass
class JournalInput:
    behavior_tracker_id: int
    answered_yes: bool
    magnitude_input_value: float | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "behavior_tracker_id": self.behavior_tracker_id,
            "answered_yes": self.answered_yes,
        }
        if self.magnitude_input_value is not None:
            d["magnitude_input_value"] = self.magnitude_input_value
            d["magnitude_input_label"] = str(int(self.magnitude_input_value))
        return d


@dataclass
class JournalBehavior:
    id: int
    title: str
    internal_name: str
    behavior_type: str
    question_text: str

    @classmethod
    def from_api(cls, data: dict) -> JournalBehavior:
        return cls(
            id=data["id"],
            title=data["title"],
            internal_name=data["internal_name"],
            behavior_type=data["behavior_type"],
            question_text=data["question_text"],
        )
