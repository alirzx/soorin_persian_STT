import numpy as np
from soorin_stt.streaming.windowed import WindowedSpeech


def test_endpoint_and_reusable_window():
    w = WindowedSpeech(16000, 0.006, 100, 200, 3)
    voice = np.ones(3200, np.float32) * .2
    silence = np.zeros(3200, np.float32)
    assert not w.push(silence)
    assert w.window_samples == 0
    assert not w.push(voice)
    assert w.has_speech()
    assert w.push(silence)
    assert w.window_samples == 6400
    assert w.seal("سلام") == "سلام"
    assert not w.window_samples
    assert w.transcript() == "سلام"


def test_window_is_bounded_at_speech_limit():
    w = WindowedSpeech(16000, .001, 100, 300, 2)
    frame = np.ones(3200, np.float32)
    for i in range(20):
        triggered = w.push(frame)
        if triggered:
            break
    assert triggered
    assert w.window_samples <= 32000
