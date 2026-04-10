# M4: thin re-export — implementation lives in fix_core
from fix_core.orchestrator.discriminator import (
    DiscriminatorQuestion,
    get_discriminator_questions,
    resolve_discriminator_answer,
)

__all__ = ["DiscriminatorQuestion", "get_discriminator_questions", "resolve_discriminator_answer"]
