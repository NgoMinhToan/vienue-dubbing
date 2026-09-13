import pytest
from apps.dubbing_web.domain import parse_srt, timing, voice_key
from apps.dubbing_web.store import Store, Conflict


def test_strict_srt_bom_multiline_and_errors():
    cues = parse_srt('\ufeff1\r\n00:00:01,000 --> 00:00:02,500\r\n<b>Xin</b>\r\nchào\r\n'.encode())
    assert cues[0]['text'] == 'Xin chào'
    assert cues[0]['start'] == 1
    with pytest.raises(ValueError, match='mục 1'):
        parse_srt(b'1\n00:00:04,000 --> 00:00:02,000\nwrong')
    with pytest.raises(ValueError):
        parse_srt(b'not an srt')


def test_gap_available_and_overflow_never_moves_start():
    fit = timing(3, 1, 5, 1)
    assert fit['speed'] == 1
    assert fit['overflow'] == 0
    fit = timing(5, 1, 3, 1, limit=1.6)
    assert fit['speed'] == 1.6
    assert fit['overflow'] == pytest.approx(1.125)
    assert timing(2, 1, 1, 1)['overflow'] == 2


def test_inherited_voice_cache_and_speed_independent():
    cue = {'text': 'Xin chào', 'voice': None}
    project = {'voice': 'Kim Thanh', 'speed': 1}
    key = voice_key(cue, project)
    project['speed'] = 2
    assert voice_key(cue, project) == key
    project['voice'] = 'Adam'
    assert voice_key(cue, project) != key


def test_revision_conflict_and_path_safety(tmp_path):
    store = Store(tmp_path)
    id, _ = store.create()
    store.save({'id': id, 'revision': 1})
    store.save({'id': id, 'revision': 2}, expected=1)
    with pytest.raises(Conflict):
        store.save({'id': id, 'revision': 2}, expected=1)
    with pytest.raises(KeyError):
        store.directory('../outside')
