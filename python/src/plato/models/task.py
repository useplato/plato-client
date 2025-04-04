from pydantic import BaseModel
from typing import Optional, Literal, List, Callable, Tuple


class BasePlatoEvalConfig(BaseModel):
    """Base configuration class for Plato evaluation settings.

    This class serves as the base configuration for different types of evaluation
    methods in the Plato system.

    Attributes:
        type (Literal["base", "state_mutation_match"]): The type of evaluation configuration.
            Can be either "base" or "state_mutation_match".
    """

    type: Literal["state_mutation_match", "custom"]


class StateMutationMatchEvalConfig(BasePlatoEvalConfig):
    """Configuration for state mutation matching evaluation.

    This class defines the configuration for evaluating tasks based on matching
    state mutations. It inherits from BasePlatoEvalConfig and specifies
    state mutations that should be matched during evaluation.

    Attributes:
        type (Literal["state_mutation_match"]): The type of evaluation, fixed as
            "state_mutation_match" for this configuration.
        state_mutations (List[dict]): A list of state mutation specifications that
            define the expected changes in state during task execution.
    """

    type: Literal["state_mutation_match"] = "state_mutation_match"
    state_mutations: List[Tuple[str, str]]


class CustomEvalConfig(BasePlatoEvalConfig):
    """Configuration for custom evaluation.

    This class defines the configuration for custom evaluation of tasks. It inherits from BasePlatoEvalConfig and specifies
    a custom evaluation function that should be used during evaluation.

    Attributes:
        type (Literal["custom"]): The type of evaluation, fixed as "custom" for this configuration.
        custom_eval_function (Callable): A custom evaluation function that should be used during evaluation.
    """

    type: Literal["custom"] = "custom"
    score_fn: Callable


class EvaluationResult(BaseModel):
    """Result of an evaluation containing both success status and reason if failed.

    Attributes:
        success: Whether the evaluation was successful
        reason: If success is False, contains the reason for failure. None if successful.
    """

    success: bool
    reason: Optional[str] = None


class PlatoTask(BaseModel):
    """Represents a task in the Plato system.

    This class defines the structure of a task, including its name, prompt, and starting URL.
    Tasks are used to specify what actions should be performed in a Plato environment.

    Attributes:
        name (str): The name of the task.
        prompt (str): The prompt describing what should be done in this task.
        start_url (str): The URL where the task should begin execution.
    """

    name: str
    prompt: str
    start_url: str
    eval_config: Optional[BasePlatoEvalConfig] = None
