"""Tests for A2A-over-MQTT requester."""

from a2a_over_mqtt.requester import _backoff_delay


class TestBackoffDelay:
    def test_backoff_within_expected_range(self):
        for _ in range(50):
            d0 = _backoff_delay(0)
            assert 0.8 <= d0 <= 1.2  # base=1.0, +-20% jitter

            d1 = _backoff_delay(1)
            assert 1.6 <= d1 <= 2.4

            d2 = _backoff_delay(2)
            assert 3.2 <= d2 <= 4.8

    def test_backoff_clamps_at_max(self):
        d = _backoff_delay(100)
        assert 3.2 <= d <= 4.8
