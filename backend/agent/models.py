from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MCQOption:
    letter: str        # "A", "B", "C", "D"
    text: str          # the option content


@dataclass
class Question:
    id: int
    text: str                        # the question itself
    options: list[MCQOption]
    chosen_letter: Optional[str] = None   # filled after user answers


@dataclass
class ClassificationResult:
    is_complex: bool
    reason: str          # why the classifier decided this way


@dataclass
class AgentSession:
    original_prompt: str
    classification: Optional[ClassificationResult] = None
    questions: list[Question] = field(default_factory=list)
    improved_prompt: Optional[str] = None