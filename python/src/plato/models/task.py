from pydantic import BaseModel, ConfigDict, field_serializer
from typing import Any, Dict, Optional, Literal, List, Callable


class BasePlatoEvalConfig(BaseModel):
    """Base configuration class for Plato evaluation settings.

    This class serves as the base configuration for different types of evaluation
    methods in the Plato system.

    Attributes:
        type (Literal["base", "state_mutation_match"]): The type of evaluation configuration.
            Can be either "base" or "state_mutation_match".
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    type: Literal["state_mutation_match", "custom"]

class StateMutationMatch(BaseModel):
    tablename: str
    action: Literal["INSERT", "UPDATE", "DELETE"]
    values: Dict[str, Any]

class MutationVariable(BaseModel):
    type: Literal["mutation_variable"] = "mutation_variable"
    name: str

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
    mutations: List[StateMutationMatch]


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
    @field_serializer('score_fn')
    def serialize_score_fn(self, score_fn: Callable, _info):
        return score_fn.__name__


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
    env_id: str
    start_url: str
    eval_config: Optional[BasePlatoEvalConfig] = None

    @field_serializer('eval_config')
    def serialize_eval_config(self, eval_config: Optional[BasePlatoEvalConfig], _info):
        return eval_config.model_dump() if eval_config else None
