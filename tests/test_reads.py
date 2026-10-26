import contextlib
import importlib.util
import io
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'client'))
import leviathan as cli
spec = importlib.util.spec_from_file_location('history', ROOT / 'examples/history_catchup.py')
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


def page(a, m, more=False):
    return dict(timeline=[], memory_revisions=[], next_contribution_cursor=a,
                next_memory_cursor=m, has_more=dict(timeline=more, memories=False))


class ReadTests(unittest.TestCase):
    def test_errors_are_not_empty_results(self):
        for command in (cli.cmd_latest, lambda: cli.cmd_thread(125)):
            for response in ((403, {'error': 'private detail'}), (503, {}), (200, {}), (200, [])):
                with self.subTest(response=response), patch.object(cli, 'request', return_value=response):
                    with self.assertRaises(SystemExit) as error:
                        command()
                    self.assertNotIn('private detail', str(error.exception))

    def test_empty_success_and_nonempty(self):
        for command, response in ((cli.cmd_latest, {'items': []}),
                                  (lambda: cli.cmd_thread(125), {'contributions': []})):
            out = io.StringIO()
            with patch.object(cli, 'request', return_value=(200, response)), contextlib.redirect_stdout(out):
                command()
            self.assertIn('succeeded', out.getvalue())
        with patch.object(cli, 'request', return_value=(200, {'items': [{'id': '12'}]})), contextlib.redirect_stdout(io.StringIO()) as out:
            cli.cmd_latest()
        self.assertIn('#12', out.getvalue())

    def test_transport_and_invalid_json(self):
        for error in (OSError('private'), ValueError('private')):
            with patch.object(cli, 'request', side_effect=error), self.assertRaises(SystemExit):
                cli.cmd_latest()

    def test_two_cursors_terminal_checkpoint(self):
        events = []
        with patch.object(history, 'read_object', side_effect=[page(100, 3, True), page(102, 3)]), contextlib.redirect_stdout(io.StringIO()):
            result = history.catch_up(consume=lambda *x: events.append('consume'),
                                      checkpoint=lambda *x: events.append(x))
        self.assertEqual(result, 0)
        self.assertEqual(events, ['consume', (100, 3), 'consume', (102, 3)])

    def test_partial_and_failed_consumer(self):
        with patch.object(history, 'read_object', return_value=page(100, 3, True)), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(history.catch_up(max_pages=1), 2)
        checkpoint = unittest.mock.Mock()
        with patch.object(history, 'read_object', return_value=page(100, 3)):
            with self.assertRaises(RuntimeError):
                history.catch_up(consume=unittest.mock.Mock(side_effect=RuntimeError()), checkpoint=checkpoint)
        checkpoint.assert_not_called()

    def test_invalid_pages_never_consumed(self):
        invalid = [page(0, 0, True), page(-1, 0), page(1, 0)]
        invalid[-1]['has_more'] = {}
        for data in invalid:
            consumer = unittest.mock.Mock()
            with patch.object(history, 'read_object', return_value=data), self.assertRaises(SystemExit):
                history.catch_up(consume=consumer)
            consumer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
