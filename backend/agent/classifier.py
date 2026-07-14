"""
classifier.py — uses Gemma 3 4B via OpenRouter for classification.
No ML model, no rules — LLM-based but ultra cheap (Gemma 3 4B costs
~$0.08/1M tokens vs GPT-4o-mini's $0.15/1M).
"""

import json
from groq import Groq

from config import (
    GROQ_API_KEY,
    CLASSIFIER_MODEL,
    CLASSIFIER_SYSTEM_PROMPT
)
from agent.models import ClassificationResult
from agent.metrics import metrics

# OpenAI client pointed at OpenRouter — same interface, different base URL
client = Groq(
    api_key=GROQ_API_KEY
)


def classify_prompt(prompt: str) -> ClassificationResult:
    """
    Sends prompt to llama-3.1-8b-instant via Groq.
    Tracks tokens + latency via metrics singleton.
    Falls back to simple on any error.
    """
    try:
        with metrics.track("Classifier", model=CLASSIFIER_MODEL) as m:
            response = client.chat.completions.create(
    model=CLASSIFIER_MODEL,
    messages=[
        {
            "role": "system",
            "content": CLASSIFIER_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"Classify: {prompt}"
        }
    ],
    temperature=0,
    max_tokens=80,
)

            # Record token usage inside the track() block
            usage = response.usage
            metrics.record_usage(
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )

        raw  = response.choices[0].message.content
        data = json.loads(raw)

        return ClassificationResult(
            is_complex=bool(data.get("is_complex", False)),
            reason=data.get("reason", "")
        )

    except Exception as e:
        return ClassificationResult(
            is_complex=False,
            reason=f"Classifier error — defaulting to simple. ({e})"
        )