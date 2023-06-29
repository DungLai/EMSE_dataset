# -*- coding: utf-8 -*-

# Import modules
from sqlalchemy import func
from sqlalchemy.sql import select

from .base import Spell
from ..backend.cores.bq import BigQueryCore

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
        
        # Get all lines-of-interests (LOIs) of fclass `on`
        lois = select(
            [
                source.c.osm_id,
                source.c.WKT,
                core.ST_GeoFromText(source.c.WKT.label('geom'))
            ],
            source.c.fclass == self.on
        ).cte('lois')

        # Create centroids for buffer
        centroids = select(
            [
                target.c[self.column].label('target_wkt'),
                core.ST_GeoFromText(target.c[self.column].label('geom'))
            ]
        ).cte('centroids')

        # Create a buffer `within` a distance/radius around each centroid. 
        # The point has to be converted to EPSG:3857 so that meters can be
        # used instead of decimal degrees for EPSG:4326.
        buff = select(
            [
                func.row_number().over().label('fid'),
                func.ST_Buffer(
                    ST_Transform(
                        centroids.c.geom,
                        3857
                    ),
                    self.within
                ).label('buff_wkt'),
                centroids.c.target_wkt
            ]
        ).select_from(centroids).cte('buff')
        
        # Clip the LOIs with the buffers then calculate the length of all
        # LOIs inside each buffer.
        clip = select(
            [
                buff.c.fid,
                func.ST_Intersection(
                    lois.c.geom,
                    func.ST_Transform(
                        buff.c.buff_wkt,
                        4326
                    )
                ).label('geom'),
                func.ST_Length(
                    func.ST_Intersection(
                        func.ST_Transform(
                            lois.c.geom,
                            3857
                        )
                    ),
                    buff.c.buff_wkt
                ).label('len')
            ],
            func.ST_Intersects(
                lois.c.source_wkt,
                func.ST_Transform(
                    buff.c.buff_wkt,
                    4326
                )
            )
        ).select_from(lois, buff).cte('clip')

        # Sum the length of all LOIs inside each buffer
        sum_length = select(
            [
                clip.c.fid,
                func.sum(clip.c.len).label('sum_len')
            ]
        ).select_from(clip).group_by(clip.c.fid).cte('sum_length')

        # Join the sum of the length of all LOIs inside each buffer
        query = (
            select(
                [
                    buff.c.fid,
                    sum_length.c.sum_len,
                    buff.c.target_wkt.label('wkt')
                ]
            ).select_from(sum_length).join(sum_length.c.fid == buff.c.fid)
        )

        return query
