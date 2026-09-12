"""Select fresh vocabulary prompts for notebook writing."""
import random


def choose_suggestions(words, previous_ids=()):
    """Choose up to three words, preferring words outside the previous prompt."""
    words = list(words)
    previous_ids = set(previous_ids)
    count = min(3, len(words))
    alternatives = [word for word in words if word['id'] not in previous_ids]
    selected = random.sample(alternatives, min(count, len(alternatives)))
    if len(selected) < count:
        previous_words = [word for word in words if word['id'] in previous_ids]
        selected.extend(random.sample(previous_words, count - len(selected)))
    random.shuffle(selected)
    return selected
