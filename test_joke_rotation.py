# -*- coding: utf-8 -*-
from fbrah_jokes import get_rotating_jokes

def test_local_jokes_are_not_misrepresented_as_external_sources():
    assert get_rotating_jokes("ar", limit=10) == []
    assert get_rotating_jokes("en", limit=10) == []
