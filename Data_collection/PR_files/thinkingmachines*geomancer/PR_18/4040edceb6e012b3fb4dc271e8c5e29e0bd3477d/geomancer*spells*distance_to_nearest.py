# -*- coding: utf-8 -*-

# Import modules
from sqlalchemy import func
from sqlalchemy.sql import select

from .base import Spell


class DistanceToNearest(Spell):
    """Obtain the distance to the nearest Point-of-Interest or geographic feature"""

    def __init__(self, on, within=10 * 1000, **kwargs):
        """
        Parameters
        ----------
        on : str
            Feature class to compare upon
        within : float, optional
            Look for values within a particular range. Its value is in meters,
            the default is :code:`10,000` meters.
        """
        super(DistanceToNearest, self).__init__(**kwargs)
        self.on = on
        self.within = within

    def query(self, source, target):
        pois = select(
            [source.c.osm_id, source.c.WKT], source.c.fclass == self.on
        ).cte("pois")
        distance = func.ST_Distance(
            func.ST_GeogFromText(target.c[self.column]), pois.c.WKT
        )
        return (
            select(
                [target, distance.label(self.feature_name)],
                distance < self.within,
            )
            .select_from(pois)
            .cte("pairs")
        )
