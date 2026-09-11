"""Local persistence and independent receptive/productive review schedules."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc)


STARTER = [
    ('reluctant', 'Not willing or eager to do something.', 'reluctant to do something', 'I was reluctant to ask for help at first.', 'You do not really want to accept an invitation. Explain how you feel.', 'adjective'),
    ('elaborate', 'To explain something in more detail.', 'elaborate on an idea', 'Could you elaborate on your suggestion?', 'A colleague gives a vague suggestion. Ask them for more detail.', 'verb'),
    ('take into account', 'To consider something when making a decision.', 'take something into account', 'We need to take travel time into account.', 'You are planning a trip. Explain why the budget matters to your decision.', 'phrase'),
    ('feasible', 'Possible and practical to do.', 'a feasible solution', 'Working from home twice a week seems feasible.', 'A friend proposes a realistic plan. Describe why it could work.', 'adjective'),
    ('drawback', 'A disadvantage or problem with something.', 'the main drawback of something', 'The main drawback of this apartment is the noise.', 'Describe one disadvantage of living in a big city.', 'noun'),
    ('prioritize', 'To decide what is most important and do it first.', 'prioritize a task', 'I need to prioritize the most urgent tasks.', 'You have too much work today. Explain how you will decide what to do first.', 'verb'),
    ('get across', 'To communicate an idea successfully.', 'get your point across', 'A simple example helped me get my point across.', 'Explain how a picture helped you communicate a complicated idea.', 'phrasal verb'),
    ('worthwhile', 'Useful or valuable enough to deserve the time or effort.', 'a worthwhile experience', 'Learning to cook has been a worthwhile experience.', 'Describe an activity that was worth your time and effort.', 'adjective'),
    ('tend to', 'To usually do something or be likely to do it.', 'tend to do something', 'I tend to concentrate better in the morning.', 'Describe something you usually do when you feel stressed.', 'phrase'),
    ('acknowledge', 'To accept or recognize that something is true.', 'acknowledge a mistake', 'She acknowledged that the deadline was unrealistic.', 'You made a mistake at work. Explain how you accept responsibility.', 'verb'),
    ('in the long run', 'Over a long period of time, rather than immediately.', 'save time in the long run', 'This extra practice will help in the long run.', 'Explain why a difficult habit could benefit your future.', 'phrase'),
    ('come up with', 'To think of an idea, answer, or plan.', 'come up with a solution', 'We came up with a simpler way to organize the files.', 'Tell someone about an idea you thought of to solve a problem.', 'phrasal verb'),
]


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY, word TEXT NOT NULL COLLATE NOCASE UNIQUE,
                meaning TEXT NOT NULL, phrase TEXT NOT NULL, example TEXT NOT NULL,
                prompt TEXT NOT NULL, kind TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS schedules (
                word_id INTEGER REFERENCES words(id), mode TEXT NOT NULL,
                due TEXT NOT NULL, interval REAL NOT NULL DEFAULT 0,
                successes INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(word_id, mode));
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY, word_id INTEGER REFERENCES words(id),
                mode TEXT, rating TEXT, response TEXT, created TEXT);
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY, body TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        ''')
        if not self.db.execute("SELECT 1 FROM settings WHERE key='seeded'").fetchone():
            for item in STARTER:
                self.add_word(*item)
            with self.db:
                self.db.execute("INSERT INTO settings VALUES ('seeded','1')")

    def add_word(self, word, meaning, phrase, example, prompt, kind='word'):
        values = [v.strip() for v in (word, meaning, phrase, example, prompt, kind)]
        if not values[0] or not values[1]:
            raise ValueError('Please enter a word and its meaning.')
        values[2] = values[2] or values[0]
        values[4] = values[4] or 'Use the word that matches this meaning in a sentence about your life.'
        values[5] = values[5] or 'word'
        with self.db:
            cursor = self.db.execute('INSERT INTO words(word,meaning,phrase,example,prompt,kind) VALUES (?,?,?,?,?,?)', values)
            for mode in ('understand', 'express'):
                self.db.execute('INSERT INTO schedules(word_id,mode,due) VALUES (?,?,?)', (cursor.lastrowid, mode, now().isoformat()))
        return cursor.lastrowid

    def words(self, query='', difficulty='all'):
        if difficulty not in ('all', 'easy', 'good', 'hard'):
            raise ValueError('Invalid vocabulary filter')
        return self.db.execute('''
            SELECT * FROM (
                SELECT w.*, (
                    SELECT r.rating FROM reviews r
                    WHERE r.word_id=w.id ORDER BY r.id DESC LIMIT 1
                ) AS last_rating
                FROM words w
            )
            WHERE instr(lower(word || ' ' || meaning || ' ' || phrase), lower(?)) > 0
              AND (
                  ?='all'
                  OR (?='hard' AND last_rating IN ('again', 'hard'))
                  OR last_rating=?
              )
            ORDER BY word
        ''', (query, difficulty, difficulty, difficulty)).fetchall()

    def due(self, mode, at=None):
        return self.db.execute('''SELECT w.*,s.interval,s.successes FROM words w JOIN schedules s ON s.word_id=w.id
            WHERE s.mode=? AND s.due<=? ORDER BY s.due,w.id''', (mode, (at or now()).isoformat())).fetchall()

    def next_interval(self, word_id, mode, rating):
        """Return the next review interval in days for a rating."""
        if mode not in ('understand', 'express') or rating not in ('again', 'hard', 'good', 'easy'):
            raise ValueError('Invalid review choice')
        if rating == 'easy':
            last = self.db.execute(
                'SELECT rating FROM reviews WHERE word_id=? AND mode=? ORDER BY id DESC LIMIT 1',
                (word_id, mode),
            ).fetchone()
            return 30 if last and last['rating'] == 'easy' else 7
        return {'again': 10 / 1440, 'hard': 1, 'good': 3}[rating]

    def review(self, word_id, mode, rating, response='', at=None):
        if mode not in ('understand', 'express') or rating not in ('again', 'hard', 'good', 'easy'):
            raise ValueError('Invalid review choice')
        at = at or now()
        previous = self.db.execute('SELECT * FROM schedules WHERE word_id=? AND mode=?', (word_id, mode)).fetchone()
        if previous is None:
            raise ValueError('Word not found')
        interval = self.next_interval(word_id, mode, rating)
        successes = 0 if rating == 'again' else previous['successes'] + 1
        with self.db:
            self.db.execute('UPDATE schedules SET due=?,interval=?,successes=? WHERE word_id=? AND mode=?', ((at + timedelta(days=interval)).isoformat(), interval, successes, word_id, mode))
            self.db.execute('INSERT INTO reviews(word_id,mode,rating,response,created) VALUES (?,?,?,?,?)', (word_id, mode, rating, response, at.isoformat()))
        return interval

    def stats(self):
        today = now().astimezone().date().isoformat()
        return {
            'words': self.db.execute('SELECT count(*) FROM words').fetchone()[0],
            'due': len(self.due('understand')) + len(self.due('express')),
            'today': self.db.execute("SELECT count(*) FROM reviews WHERE date(created,'localtime')=?", (today,)).fetchone()[0],
            'growing': self.db.execute("SELECT count(*) FROM schedules WHERE mode='express' AND successes>=3").fetchone()[0],
        }

    def save_note(self, body):
        if not body.strip():
            raise ValueError('Write something before saving.')
        with self.db:
            self.db.execute('INSERT INTO notes(body,created) VALUES (?,?)', (body.strip(), now().isoformat()))

    def notes(self):
        return self.db.execute('SELECT * FROM notes ORDER BY id DESC').fetchall()

    def export(self, path):
        data = {table: [dict(row) for row in self.db.execute('SELECT * FROM ' + table)] for table in ('words', 'schedules', 'reviews', 'notes')}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def close(self):
        self.db.close()
