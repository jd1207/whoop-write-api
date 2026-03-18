from importlib.metadata import version, PackageNotFoundError

from whoop.client import WhoopClient
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement,
    WorkoutWrite, ExerciseWrite, SportTypeInfo, WorkoutResult,
    ActivityResult, JournalInput, JournalBehavior,
    DetailedExercise, ExerciseSet,
)
from whoop.sport_types import SportType
from whoop.exceptions import WhoopAuthError, WhoopAPIError, WhoopRateLimitError

try:
    __version__ = version("whoop-write-api")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = [
    "WhoopClient",
    "Recovery", "Sleep", "Workout", "Cycle", "BodyMeasurement",
    "WorkoutWrite", "ExerciseWrite", "SportTypeInfo", "WorkoutResult",
    "ActivityResult", "JournalInput", "JournalBehavior",
    "DetailedExercise", "ExerciseSet",
    "SportType",
    "WhoopAuthError", "WhoopAPIError", "WhoopRateLimitError",
    "__version__",
]
