"""English definitions from Free Dictionary API; no account or API key."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class LookupError(Exception):
    pass


def lookup(word):
    word = word.strip()
    if not word:
        raise LookupError('Enter an English word first.')
    request = Request('https://api.dictionaryapi.dev/api/v2/entries/en/' + quote(word, safe=''),
                      headers={'User-Agent': 'Wordcraft/1.1', 'Accept': 'application/json'})
    try:
        with urlopen(request, timeout=10) as response:
            data = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise LookupError('No definition found. Check the spelling, try a single word, or enter a meaning yourself.') from exc
        raise LookupError('The dictionary is unavailable right now. Try again or enter a meaning yourself.') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise LookupError('Could not reach the dictionary. Check your internet connection or enter a meaning yourself.') from exc
    except (ValueError, UnicodeError) as exc:
        raise LookupError('The dictionary returned an unreadable response. Please try again.') from exc
    return parse_definitions(data)


def parse_definitions(data):
    results = []
    seen = set()
    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            for meaning in entry.get('meanings', []) or []:
                if not isinstance(meaning, dict):
                    continue
                kind = meaning.get('partOfSpeech') or 'word'
                for definition in meaning.get('definitions', []) or []:
                    if not isinstance(definition, dict):
                        continue
                    text = definition.get('definition')
                    if not isinstance(text, str) or not text.strip():
                        continue
                    key = (kind, text.strip())
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({'meaning': text.strip(), 'kind': kind,
                                    'example': definition.get('example') or ''})
    if not results:
        raise LookupError('No usable definition found. You can enter a meaning yourself.')
    return results
