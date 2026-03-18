from __future__ import annotations
from dataclasses import dataclass

from whoop.write_models import Exercise


@dataclass
class ExerciseCatalog:
    exercises: list[Exercise]
    equipment_types: list[str]
    muscle_groups: list[str]
    movement_patterns: list[str]

    def find_by_id(self, exercise_id: str) -> Exercise | None:
        for ex in self.exercises:
            if ex.exercise_id == exercise_id:
                return ex
        return None

    def search(self, query: str) -> list[Exercise]:
        q = query.lower()
        return [
            ex for ex in self.exercises
            if q in ex.name.lower() or q in ex.exercise_id.lower()
        ]

    def filter(
        self,
        equipment: str | None = None,
        muscle_group: str | None = None,
        movement_pattern: str | None = None,
    ) -> list[Exercise]:
        results = self.exercises
        if equipment:
            results = [ex for ex in results if ex.equipment == equipment]
        if muscle_group:
            results = [
                ex for ex in results if muscle_group in ex.muscle_groups
            ]
        if movement_pattern:
            results = [
                ex for ex in results
                if ex.movement_pattern == movement_pattern
            ]
        return results

    @classmethod
    def from_api(cls, data: dict) -> ExerciseCatalog:
        exercises = [
            Exercise.from_api(ex) for ex in data.get("exercises", [])
        ]
        filters = data.get("filter_options", {})
        return cls(
            exercises=exercises,
            equipment_types=[
                f["internal_value"] for f in filters.get("equipment", [])
            ],
            muscle_groups=[
                f["internal_value"]
                for f in filters.get("muscle_groups", [])
            ],
            movement_patterns=[
                f["internal_value"]
                for f in filters.get("movement_patterns", [])
            ],
        )
