"""Pure-Python scoring shared by pilot and placement experiments."""

import re
from collections import Counter


def label(answer, choices=None):
    match = re.match(r"^\s*[\(\[]?([A-E])[\)\]]?(?=$|[\s.:;,)\-])", str(answer))
    if match:
        return match.group(1)
    if choices:
        normalize = lambda text: re.sub(r"\s+", " ", str(text)).strip().strip(" .!\"'*").casefold()
        matches = [option for option, text in zip(choices["label"], choices["text"]) if normalize(answer) == normalize(text)]
        if len(matches) == 1:
            return matches[0]
    return None


def evaluate(labels, gold, target):
    count = Counter(x for x in labels if x is not None)
    majority = next((x for x, n in count.items() if n > len(labels) / 2), None)
    return {
        "n_agents": len(labels), "correct": labels.count(gold),
        "target_adoptions": labels.count(target), "invalid": labels.count(None),
        "majority": majority, "system_correct": int(majority == gold),
        "system_target": int(majority == target), "no_majority": int(majority is None),
    }


def declared_answer(response, choices):
    """Audit explicit answer fields independently of reasoning/memory parsing.

    Prefer UPDATED ANSWER fields. Multiple differing valid declarations remain
    ambiguous; placeholders and commentary are not interpreted as answers.
    This is a scoring sensitivity check, not a rerun with repaired agent state.
    """
    pattern = re.compile(
        r"^\s*(?:\*\*)?<?(?:YOUR\s+)?(?P<updated>UPDATED[_ ]+)?ANSWER>?(?:\*\*)?\s*:\s*(?P<value>[^\n]+)",
        re.MULTILINE | re.IGNORECASE,
    )
    matches = list(pattern.finditer(response))
    updated = [m for m in matches if m.group("updated")]
    selected = updated if updated else matches
    predictions = {label(m.group("value").strip().strip("*"), choices) for m in selected}
    predictions.discard(None)
    return next(iter(predictions)) if len(predictions) == 1 else None
