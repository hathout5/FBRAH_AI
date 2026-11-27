import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import fbrah_reminder_worker as worker

def test_arabic_toast_text_is_normalized_and_rtl_isolated():
    result = worker._rtl_toast_text('اختار   تنبيه اجتماع')
    assert result.startswith('\u200f\u2067')
    assert result.endswith('\u2069\u200f')
    assert 'اختار تنبيه اجتماع' in result
    assert '\ufeff' not in result

def test_sound_config_accepts_all_tones_and_clamps_values(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, 'BASE_DIR', tmp_path)
    (tmp_path / 'fbrah_reminder_sound.json').write_text(
        json.dumps({'tone':'chime','volume':130,'repeats':20}), encoding='utf-8'
    )
    assert worker._sound_settings() == {'tone':'chime','volume':100,'repeats':10}

def test_sound_config_falls_back_for_invalid_values(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, 'BASE_DIR', tmp_path)
    (tmp_path / 'fbrah_reminder_sound.json').write_text(
        json.dumps({'tone':'invalid','volume':-5,'repeats':0}), encoding='utf-8'
    )
    assert worker._sound_settings() == {'tone':'classic','volume':0,'repeats':1}
