# -*- coding: utf-8 -*-

# Import modules
from sqlalchemy import func
from sqlalchemy.sql import select

from .base import Spell


class LengthOf(Spell):
    """Obtain the length of all Lines-of-Interest within a certain radius"""

    def __init__(self, on, within=10 * 1000, **kwargs):
        """Spell constructor

        Parameters
        ----------
        on : str
            Feature class to compare upon
        within : float, optional
            Look for values within a particular range. Its value is in meters,
            the default is :code:`10,000` meters.
        source_table : str
            Table URI to run queries against.
        feature_name : str
            Column name for the output feature.
        column : str, optional
            Column to look the geometries from. The default is :code:`WKT`
        options : geomancer.Config
            Specify configuration for interacting with the database backend.
            Default is a BigQuery Configuration
        """
        super(LengthOf, self).__init__(**kwargs)
        self.on = on
        self.within = within

    def query(self, source, target, core):
        # ST_Buffer is not yet implemented so BigQueryCore won't work
        # (groups.google.com/d/msg/bq-gis-feedback/Yq4Ku6u2A80/ceVXU01RCgAJ)
        if isinstance(core, BigQueryCore):
            raise ValueError(
                "The LengthOf feature is currently incompatible with \
                BigQueryCore because ST_Buffer is not yet implemented"
            )
        # Get all lines-of-interest of fclass `on`
        lines_of_interest = select(
            [source.c.osm_id, source.c.WKT], source.c.fclass == self.on
        ).cte("lines_of_interest")
        # Create a buffer `within` a distance/radius around each `column` 
        buff = func.ST_Buffer(
            core.ST_GeoFromText(target.c[self.column]),
            self.within,
        )
        # Clip the lines-of-interest with the buffer
        clip = func.ST_Intersection(
            core.ST_GeoFromText(source.c.WKT),
            buff.c.WKT,
        )
        # Find the length of the clipped lines-of-interest
        length = func.ST_Length(
            clip.WKT,
        )
        return length
