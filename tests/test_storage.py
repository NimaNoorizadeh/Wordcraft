import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from storage import Store


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'words.db'
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_review_modes_are_independent_and_persist(self):
        at = datetime.now(timezone.utc) + timedelta(seconds=1)
        word = self.store.due('express', at)[0]
        self.store.review(word['id'], 'express', 'good', 'My sentence', at)
        self.assertNotIn(word['id'], [w['id'] for w in self.store.due('express', at)])
        self.assertIn(word['id'], [w['id'] for w in self.store.due('understand', at)])
        self.assertNotIn(word['id'], [w['id'] for w in self.store.due('express', at + timedelta(days=2))])
        self.assertIn(word['id'], [w['id'] for w in self.store.due('express', at + timedelta(days=3))])
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(len(self.store.words()), 12)
        self.assertEqual(self.store.db.execute('SELECT response FROM reviews').fetchone()[0], 'My sentence')

    def test_failed_recall_returns_in_ten_minutes(self):
        at = datetime.now(timezone.utc) + timedelta(seconds=1)
        word = self.store.due('express', at)[0]
        self.store.review(word['id'], 'express', 'easy', at=at)
        self.store.review(word['id'], 'express', 'again', at=at)
        self.assertNotIn(word['id'], [w['id'] for w in self.store.due('express', at + timedelta(minutes=9))])
        self.assertIn(word['id'], [w['id'] for w in self.store.due('express', at + timedelta(minutes=10))])
        self.assertEqual(self.store.db.execute("SELECT successes FROM schedules WHERE word_id=? AND mode='express'", (word['id'],)).fetchone()[0], 0)

    def test_easy_twice_schedules_one_month(self):
        at = datetime.now(timezone.utc) + timedelta(seconds=1)
        word = self.store.due('express', at)[0]
        self.assertEqual(self.store.review(word['id'], 'express', 'easy', at=at), 7)
        self.assertEqual(self.store.next_interval(word['id'], 'express', 'easy'), 30)
        self.assertEqual(self.store.review(word['id'], 'express', 'easy', at=at + timedelta(days=7)), 30)

    def test_non_easy_rating_breaks_easy_streak(self):
        at = datetime.now(timezone.utc) + timedelta(seconds=1)
        word = self.store.due('express', at)[0]
        self.store.review(word['id'], 'express', 'easy', at=at)
        self.store.review(word['id'], 'express', 'good', at=at + timedelta(days=7))
        self.assertEqual(self.store.next_interval(word['id'], 'express', 'easy'), 7)

    def test_custom_word_and_notebook_export(self):
        self.store.add_word('nuance', 'A subtle difference.', 'a subtle nuance', 'I missed that nuance.', 'Explain a small difference.', 'noun')
        self.assertEqual(len(self.store.words('NUANCE')), 1)
        self.store.save_note('I noticed a subtle nuance.')
        output = Path(self.temp.name) / 'export.json'
        self.store.export(output)
        data = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(len(data['words']), 13)
        self.assertEqual(len(data['schedules']), 26)
        self.assertEqual(data['notes'][0]['body'], 'I noticed a subtle nuance.')

    def test_word_with_only_definition_can_be_saved(self):
        self.store.add_word('insight', 'A clear understanding.', '', '', '', '')
        word = self.store.words('insight')[0]
        self.assertEqual(word['phrase'], 'insight')
        self.assertEqual(word['example'], '')
        self.assertTrue(word['prompt'])
        self.assertEqual(word['kind'], 'word')

    def test_vocabulary_filters_use_the_latest_rating(self):
        at = datetime.now(timezone.utc) + timedelta(seconds=1)
        words = self.store.words()
        easy_word, good_word, hard_word = words[:3]
        self.store.review(easy_word['id'], 'express', 'easy', at=at)
        self.store.review(good_word['id'], 'express', 'good', at=at)
        self.store.review(hard_word['id'], 'express', 'again', at=at)

        self.assertEqual([w['id'] for w in self.store.words(difficulty='easy')], [easy_word['id']])
        self.assertEqual([w['id'] for w in self.store.words(difficulty='good')], [good_word['id']])
        self.assertEqual([w['id'] for w in self.store.words(difficulty='hard')], [hard_word['id']])

        self.store.review(easy_word['id'], 'understand', 'hard', at=at + timedelta(minutes=1))
        self.assertNotIn(easy_word['id'], [w['id'] for w in self.store.words(difficulty='easy')])
        self.assertIn(easy_word['id'], [w['id'] for w in self.store.words(difficulty='hard')])


if __name__ == '__main__':
    unittest.main()
