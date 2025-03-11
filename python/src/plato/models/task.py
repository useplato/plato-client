from pydantic import BaseModel
from typing import Optional, Literal, List


class BasePlatoEvalConfig(BaseModel):
    """Base configuration class for Plato evaluation settings.

    This class serves as the base configuration for different types of evaluation
    methods in the Plato system.

    Attributes:
        type (Literal["base", "state_mutation_match"]): The type of evaluation configuration.
            Can be either "base" or "state_mutation_match".
    """
    type: Literal["base", "state_mutation_match"]


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
    state_mutations: List[dict]


class PlatoTask(BaseModel):
    """Represents a task in the Plato system.

    This class defines the structure of a task, including its name, metadata,
    initial state, and evaluation configuration.

    Attributes:
        name (Optional[str]): The name of the task. Defaults to None.
        metadata (Optional[dict]): Additional metadata associated with the task.
            Defaults to None.
        initial_state (Optional[dict]): The initial state of the task before
            execution. Defaults to None.
        eval_config (Optional[BasePlatoEvalConfig]): The evaluation configuration
            for the task. Defaults to None.
    """
    name: Optional[str] = None
    metadata: Optional[dict] = None
    initial_state: Optional[dict] = None
    eval_config: Optional[BasePlatoEvalConfig] = None