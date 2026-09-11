import json
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_provider import Cancelled, CodexProvider, LookupError, Session, SignInRequired, parse_generated


ENTRY = {'valid': True, 'message': '',
         'meaning': 'Able to recover after difficulty.',
         'examples': ['She is resilient.', 'Our team stayed resilient.']}


class FakeSession:
    calls = []
    fail = False

    def __init__(self, *args):
        self.events = iter([
            {'method': 'item/completed', 'params': {'threadId': 'other', 'item': {'type': 'agentMessage', 'text': 'unrelated'}}},
            {'method': 'item/completed', 'params': {'threadId': 'word-thread', 'item': {'type': 'agentMessage', 'phase': 'final_answer', 'text': json.dumps(ENTRY)}}},
            {'method': 'turn/completed', 'params': {'threadId': 'word-thread', 'turn': {'status': 'failed' if self.fail else 'completed', 'error': {'message': 'Usage limit reached'}}}}
        ])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def account(self):
        return {'type': 'chatgpt'}

    def call(self, method, params):
        self.calls.append((method, params))
        return {'thread': {'id': 'word-thread'}, 'turn': {'id': 'word-turn'}}

    def event(self, deadline):
        return next(self.events)


class ProviderTests(unittest.TestCase):
    def test_complete_generated_entry(self):
        result = parse_generated(json.dumps(ENTRY))[0]
        self.assertEqual(result['example'].splitlines(), ENTRY['examples'])
        self.assertEqual(result['meaning'], ENTRY['meaning'])
        self.assertNotIn('phrase', result)
        self.assertNotIn('prompt', result)

    def test_reject_invalid_and_incomplete_entries(self):
        for value in ('not json', '{}',
                      json.dumps({'valid': True, 'message': '', 'meaning': 'partial', 'examples': []}),
                      json.dumps({'valid': True, 'message': '', 'meaning': 'partial', 'examples': ['Only one.']})):
            with self.subTest(value=value), self.assertRaises(LookupError):
                parse_generated(value)
        with self.assertRaisesRegex(LookupError, 'Check spelling'):
            parse_generated(json.dumps({'valid': False, 'message': 'Check spelling',
                                        'meaning': '', 'examples': ['', '']}))

    def test_refuses_api_key_and_signed_out_accounts(self):
        session = object.__new__(Session)
        for account in (None, {'type': 'apiKey'}):
            session.call = lambda *args: {'account': account}
            with self.assertRaises(SignInRequired):
                session.account()

    def test_generation_is_cached_without_another_session(self):
        with tempfile.TemporaryDirectory() as folder, patch('codex_provider.Session', FakeSession):
            FakeSession.calls = []
            provider = CodexProvider(folder)
            first = provider.generate('resilient')
            self.assertEqual(first[0]['meaning'], ENTRY['meaning'])
            self.assertEqual(FakeSession.calls[0][1]['sandbox'], 'read-only')
            self.assertTrue(FakeSession.calls[0][1]['ephemeral'])
            instructions = FakeSession.calls[0][1]['developerInstructions']
            self.assertIn('25 to 45 words', instructions)
            self.assertIn('12 to 25 words', instructions)
            with patch('codex_provider.Session', side_effect=AssertionError('Cache should avoid a process')):
                self.assertIn('saved result', provider.generate('Resilient')[0]['source'])

    def test_failed_turn_is_not_cached(self):
        with tempfile.TemporaryDirectory() as folder, patch('codex_provider.Session', FakeSession):
            FakeSession.fail = True
            try:
                provider = CodexProvider(folder)
                with self.assertRaisesRegex(LookupError, 'Usage limit'):
                    provider.generate('resilient')
                self.assertEqual(list(provider.cache_dir.glob('*.json')), [])
            finally:
                FakeSession.fail = False

    def test_cancellation_and_process_exit(self):
        session = object.__new__(Session)
        session.cancel = threading.Event()
        session.inbox = queue.Queue()
        session.cancel.set()
        with self.assertRaises(Cancelled):
            session.receive(time.monotonic() + 1)
        session.cancel.clear()
        session.inbox.put(None)
        with self.assertRaisesRegex(LookupError, 'stopped'):
            session.receive(time.monotonic() + 1)

    def test_unsolicited_tool_requests_are_rejected(self):
        session = object.__new__(Session)
        session.cancel = threading.Event()
        session.inbox = queue.Queue()
        session.inbox.put({'method': 'item/tool/call', 'id': 99})
        session.inbox.put({'method': 'turn/completed'})
        sent = []
        session.send = sent.append
        self.assertEqual(session.receive(time.monotonic() + 1)['method'], 'turn/completed')
        self.assertEqual(sent[0]['error']['code'], -32601)


if __name__ == '__main__':
    unittest.main()
