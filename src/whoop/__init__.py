from importlib.metadata import version, PackageNotFoundError

from whoop.client import WhoopClient
from whoop.cognito import CognitoAuth, TokenSet
from whoop.models import (
    Recovery, Sleep, Workout, Cycle, BodyMeasurement,
    WorkoutWrite, ExerciseWrite, SportTypeInfo, WorkoutResult,
    ActivityResult, JournalInput, JournalBehavior,
    DetailedExercise, ExerciseSet,
)
from whoop.write_models import Exercise
from whoop.write_exercises import ExerciseCatalog
from whoop.sport_types import SportType
from whoop.exceptions import (
    WhoopAuthError, WhoopAPIError, WhoopRateLimitError,
    WhoopAuthExpiredError,
)

try:
    __version__ = version("whoop-write-api")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = [
    "WhoopClient",
    "CognitoAuth", "TokenSet",
    "Recovery", "Sleep", "Workout", "Cycle", "BodyMeasurement",
    "WorkoutWrite", "ExerciseWrite", "SportTypeInfo", "WorkoutResult",
    "ActivityResult", "JournalInput", "JournalBehavior",
    "DetailedExercise", "ExerciseSet",
    "Exercise", "ExerciseCatalog",
    "SportType",
    "WhoopAuthError", "WhoopAPIError", "WhoopRateLimitError",
    "WhoopAuthExpiredError",
    "__version__",
]
