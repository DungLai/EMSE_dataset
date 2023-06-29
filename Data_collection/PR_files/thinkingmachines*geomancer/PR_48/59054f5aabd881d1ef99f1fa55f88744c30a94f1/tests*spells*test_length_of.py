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
            on="primary",
            source_table="gis_osm_roads_free_1",
            feature_name="dist_primary",
            options=SQLiteConfig(),
        ),
        host="tests/data/source.sqlite",
    ),
    pytest.param(
        SpellHost(
            spell=DistanceToNearest(
                on="primary",
                source_table="tm-geospatial.ph_osm.gis_osm_roads_free_1",
                feature_name="dist_primary",
                options=BQConfig(),
            ),
            host=bigquery.Client,
        ),
        marks=pytest.mark.bqtest,
    ),
]


class TestLengthOf(BaseTestSpell):
    @pytest.fixture(
        params=params,
        ids=["roads-sqlite", "roads-bq"],
    )
    def spellhost(self, request):
        return request.param
