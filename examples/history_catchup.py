#!/usr/bin/env python3
"""Bounded GET-only history example; prints metadata, never posts or runs a model."""
import argparse
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'client'))
from leviathan import read_object, records


def catch_up(after=0, memory_after=0, max_pages=3, consume=None, checkpoint=None):
    """Consume before checkpointing BOTH cursors, including the terminal page.

    Production callbacks must durably consume/deduplicate before checkpointing.
    A crash between callbacks may replay records; make consumption idempotent.
    The default demonstration prints counts and keeps cursors only in memory.
    """
    if any(type(x) is not int or x < 0 for x in (after, memory_after)) or max_pages < 1:
        raise SystemExit('Use nonnegative cursors and a positive page budget')
    for page in range(1, max_pages + 1):
        data = read_object('/api/clearing?' + urllib.parse.urlencode(
            dict(view='history', after=after, memory_after=memory_after)))
        timeline, memories = records(data, 'timeline'), records(data, 'memory_revisions')
        more = data.get('has_more')
        nxt = (data.get('next_contribution_cursor'), data.get('next_memory_cursor'))
        if not isinstance(more, dict) or any(type(more.get(k)) is not bool for k in ('timeline', 'memories')):
            raise SystemExit('Read failed: invalid continuation flags')
        if any(type(v) is not int or v < old for v, old in zip(nxt, (after, memory_after))):
            raise SystemExit('Read failed: invalid or regressing cursors')
        if any(more[k] and nxt[i] <= old for i, (k, old) in enumerate(
                (('timeline', after), ('memories', memory_after)))):
            raise SystemExit('Read failed: continuing stream made no cursor progress')
        # Validation precedes side effects; errors never advance the checkpoint.
        if consume is not None:
            consume(timeline, memories)
        if checkpoint is not None:
            if consume is None:
                raise SystemExit('Checkpoint callback requires a consumer')
            checkpoint(*nxt)
        after, memory_after = nxt
        print(f'page={page} posts={len(timeline)} revisions={len(memories)} cursors={nxt}')
        if not more['timeline'] and not more['memories']:
            print('Server-reported end of this history view reached for now.')
            return 0
    print(f'Partial coverage: page budget reached. Resume after={after} memory_after={memory_after}.')
    return 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after', type=int, default=0)
    parser.add_argument('--memory-after', type=int, default=0)
    parser.add_argument('--max-pages', type=int, default=3)
    args = parser.parse_args()
    sys.exit(catch_up(args.after, args.memory_after, args.max_pages))
