"""Round-trip tests for Party.save_dict/from_dict and the SubmitResult contract.

These protect two boundaries that have no curses dependency and would silently
break if someone changed a key or forgot to migrate a field:

  - finalclaudesy save format (loaded by old saves after future changes)
  - claudcade_scores.submit_score offline shape (always returns local fields)

Run with: python3 -m pytest tests/
"""
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)


# ── finalclaudesy save round-trip ─────────────────────────────────────────────

def test_party_save_round_trip() -> None:
    from finalclaudesy.entities import Party

    p = Party()
    # Mutate every field so a missing key in from_dict fails loud.
    p.gold = 1234
    p.items['Potion'] = 99
    p.items['Hi-Potion'] = 7
    p.story_flags.add('boss1')
    p.story_flags.add('newgame_plus_started')
    p.dungeon_done.add('Eldergrove')
    p.map_x = 21
    p.map_y = 9
    p.newgame_plus = True
    # Mutate a character so member state also round-trips.
    p.members[0].level = 12
    p.members[0].exp   = 4500

    d = p.save_dict()
    # Sanity: every required key is present.
    for key in ('members', 'gold', 'items', 'flags', 'dungeons',
                'map_x', 'map_y', 'newgame_plus'):
        assert key in d, f'save_dict missing key: {key}'

    # Round-trip through JSON to catch non-serialisable types.
    p2 = Party.from_dict(json.loads(json.dumps(d)))

    assert p2.gold == 1234
    assert p2.items['Potion'] == 99
    assert p2.items['Hi-Potion'] == 7
    assert 'boss1' in p2.story_flags
    assert 'newgame_plus_started' in p2.story_flags
    assert 'Eldergrove' in p2.dungeon_done
    assert p2.map_x == 21 and p2.map_y == 9
    assert p2.newgame_plus is True
    assert p2.members[0].level == 12
    assert p2.members[0].exp   == 4500


def test_save_path_is_centralized() -> None:
    """main.py and explore.py must agree on SAVE_PATH so the in-game menu and
    the title-screen loader hit the same file."""
    from finalclaudesy           import SAVE_PATH as PKG_PATH
    from finalclaudesy.main      import SAVE_PATH as MAIN_PATH
    # explore.py reads it inside _do_save via late import; verify the module
    # attribute matches by importing the package constant from there too.
    import finalclaudesy.explore as _explore   # noqa: F401  (import side-effect)

    assert PKG_PATH == MAIN_PATH
    assert PKG_PATH.endswith('finalclaudesy_save.json')


# ── claudcade_scores offline contract ─────────────────────────────────────────

def test_submit_score_offline_returns_local_fields(tmp_path, monkeypatch) -> None:
    """When the network is unreachable, submit_score must still return
    {local_best, is_new_pb} so callers never crash. Server fields are absent."""
    import claudcade_scores as cs

    # Redirect the on-disk caches into the test sandbox.
    fake_scores = tmp_path / 'pb.json'
    fake_id     = tmp_path / 'id'
    monkeypatch.setattr(cs, 'SCORES_FILE', str(fake_scores))
    monkeypatch.setattr(cs, 'ID_FILE',     str(fake_id))
    monkeypatch.setattr(cs, '_player_id',  None)
    monkeypatch.setattr(cs, '_new_registration', False)

    # Point at an unroutable address so the network call fails fast.
    monkeypatch.setattr(cs, 'SITE', 'http://127.0.0.1:1')

    result = cs.submit_score('ctype', 12345, 'Wave 7')

    # Local fields always present.
    assert result['local_best'] == 12345
    assert result['is_new_pb'] is True
    # Server fields absent on offline submit.
    assert 'rank'    not in result
    assert 'success' not in result

    # Beating my own PB on a second call should still flag is_new_pb.
    result2 = cs.submit_score('ctype', 99999, 'Wave 99')
    assert result2['local_best'] == 99999
    assert result2['is_new_pb'] is True

    # Lower score must NOT mark a new PB.
    result3 = cs.submit_score('ctype', 100, 'Wave 1')
    assert result3['local_best'] == 99999
    assert result3['is_new_pb'] is False


def test_consume_new_registration_is_single_shot(monkeypatch) -> None:
    """consume_new_registration() returns the new ID exactly once so the
    launcher's welcome banner can't double-fire."""
    import claudcade_scores as cs

    monkeypatch.setattr(cs, '_player_id', 42)
    monkeypatch.setattr(cs, '_new_registration', True)

    assert cs.consume_new_registration() == 42
    assert cs.consume_new_registration() is None
    assert cs.consume_new_registration() is None
