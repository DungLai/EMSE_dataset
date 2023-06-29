# -*- coding: utf-8 -*-

# Import modules
import pytest
from google.cloud import bigquery
from tests.spells.base_test_spell import BaseTestSpell, SpellHost

# Import from package
from geomancer.backend.settings import BQConfig, SQLiteConfig
from geomancer.spells import LengthOf

params = [
    SpellHost(
        spell=LengthOf(
            on="residential",
            within=50,
            source_table="gis_osm_roads_free_1",
            feature_name="len_residential",
            options=SQLiteConfig(),
        ),
        host="tests/data/source.sqlite",
    )
]


class TestLengthOf(BaseTestSpell):
    @pytest.fixture(params=params, ids=["roads-sqlite"])
    def spellhost(self, request):
        return request.param
