import logging as std_logging
from types import SimpleNamespace

import nexor.logging as nexor_logging


def test_map_loguru_level_defaults_to_info_for_unknown_names():
    assert nexor_logging._map_loguru_level('never heard of this') == std_logging.INFO


def test_configure_loguru_logging_adds_sink_and_skips_second_call(monkeypatch):
    remove_called = False
    add_calls = []

    def fake_remove():
        nonlocal remove_called
        remove_called = True

    def fake_add(*args, **kwargs):
        add_calls.append((args, kwargs))

    monkeypatch.setattr(nexor_logging, '_configured_loguru', False)
    monkeypatch.setattr(nexor_logging.logger, 'remove', fake_remove)
    monkeypatch.setattr(nexor_logging.logger, 'add', fake_add)

    settings = SimpleNamespace(
        log_level='DEBUG',
        log_enqueue=False,
        log_backtrace=False,
        log_diagnose=False,
        log_console_plain=True,
    )

    nexor_logging.configure_loguru_logging(settings=settings)

    assert remove_called
    assert len(add_calls) == 1
    assert add_calls[0][1]['level'] == 'DEBUG'

    nexor_logging.configure_loguru_logging(settings=settings)
    assert len(add_calls) == 1
