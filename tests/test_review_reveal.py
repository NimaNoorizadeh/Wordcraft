import unittest

from app import format_review_reveal


class ReviewRevealTests(unittest.TestCase):
    def setUp(self):
        self.word = {
            'word': 'credence',
            'phrase': 'credence',
            'meaning': 'Belief in or acceptance of something as true.',
            'example': 'The evidence lent credence to the theory.\nThey gave little credence to the claim.',
        }

    def test_expression_reveal_shows_word_once_and_examples_only(self):
        heading, details = format_review_reveal(self.word, 'express')
        self.assertEqual(heading, 'credence')
        self.assertEqual(details, self.word['example'])
        self.assertNotIn(self.word['meaning'], details)

    def test_understanding_reveal_keeps_meaning(self):
        heading, details = format_review_reveal(self.word, 'understand')
        self.assertEqual(heading, 'credence')
        self.assertEqual(details, self.word['meaning'] + '\n' + self.word['example'])

    def test_distinct_phrase_is_kept(self):
        self.word['phrase'] = 'lend credence to something'
        heading, _ = format_review_reveal(self.word, 'express')
        self.assertEqual(heading, 'credence  ·  lend credence to something')


if __name__ == '__main__':
    unittest.main()
