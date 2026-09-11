import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from dictionary_lookup import LookupError, lookup, parse_definitions


class DictionaryTests(unittest.TestCase):
    def test_multiple_senses_deduplicate_and_optional_examples(self):
        data = [{'meanings': [{'partOfSpeech': 'noun', 'definitions': [
            {'definition': 'A first meaning.', 'example': 'An example.'},
            {'definition': 'Another meaning.'}, {'definition': 'A first meaning.'}]}]}]
        results = parse_definitions(data)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['example'], 'An example.')
        self.assertEqual(results[1]['example'], '')

    def test_lookup_url_is_encoded(self):
        with patch('dictionary_lookup.urlopen', return_value=io.BytesIO(b'[{"meanings":[{"definitions":[{"definition":"A phrase."}]}]}]')) as request:
            self.assertEqual(lookup('take off')[0]['meaning'], 'A phrase.')
            self.assertTrue(request.call_args.args[0].full_url.endswith('take%20off'))
            self.assertEqual(request.call_args.kwargs['timeout'], 10)

    def test_failure_messages(self):
        for error, expected in [(HTTPError('url', 404, 'missing', {}, None), 'No definition found'),
                                (URLError('offline'), 'internet connection')]:
            with self.subTest(error=error), patch('dictionary_lookup.urlopen', side_effect=error):
                with self.assertRaisesRegex(LookupError, expected):
                    lookup('word')
        with self.assertRaises(LookupError):
            parse_definitions({'title': 'No Definitions Found'})


if __name__ == '__main__':
    unittest.main()
