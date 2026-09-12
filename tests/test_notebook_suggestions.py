import unittest

from notebook_suggestions import choose_suggestions


class NotebookSuggestionTests(unittest.TestCase):
    def test_enough_alternatives_avoid_all_previous_words(self):
        words = [{'id': number} for number in range(8)]
        selected = choose_suggestions(words, [0, 1, 2])
        ids = {word['id'] for word in selected}
        self.assertEqual(len(ids), 3)
        self.assertTrue(ids.isdisjoint({0, 1, 2}))

    def test_small_vocabulary_still_changes_the_combination(self):
        words = [{'id': number} for number in range(4)]
        ids = {word['id'] for word in choose_suggestions(words, [0, 1, 2])}
        self.assertEqual(len(ids), 3)
        self.assertIn(3, ids)
        self.assertNotEqual(ids, {0, 1, 2})

    def test_three_or_fewer_words_are_all_available(self):
        for size in range(4):
            with self.subTest(size=size):
                words = [{'id': number} for number in range(size)]
                selected = choose_suggestions(words, range(size))
                self.assertEqual({word['id'] for word in selected}, set(range(size)))


if __name__ == '__main__':
    unittest.main()
