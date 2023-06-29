# -*- coding: utf-8 -*-

# Import modules
import pandas as pd
from loguru import logger
from sqlalchemy import func, literal_column
from sqlalchemy.engine import create_engine
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql import select

# Import from package
from google.cloud import bigquery

from .base import Spell
from ..common import bqutils as bq
from ..common.settings import BQConfig


class DistanceToNearest(Spell):
    """Obtain the distance to the nearest Point-of-Interest or geographic feature"""

    def __init__(self):
        super(DistanceToNearest, self).__init__()

    @classmethod
    def cast(
        cls,
        on,
        df,
        client,
        database_url,
        source_table,
        feature_name,
        column='geometry',
        within=10 * 1000,
        bq_options=BQConfig,
        **kwargs
    ):
        """Apply the feature transform to an input pandas.DataFrame

        Parameters
        ----------
        on : str
            Feature class to compare upon
        df : pandas.DataFrame
            Dataframe containing the points to compare upon. By default, we
            will look into the :code:`geometry` column. You can specify your
            own column by passing an argument to the :code:`column` parameter.
        client : google.cloud.client.Client
            Cloud Client for making requests.
        database_url: str
            Database URL to connect to.
            https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
        source_table : str
            BigQuery table to run queries against.
        feature_name : str
            Column name for the output feature.
        column : str, optional
            Column to look the geometries from. The default is :code:`geometry`
        within : float, optional
            Look for values within a particular range. Its value is in meters,
            the default is :code:`10,000` meters.
        bq_options : geomancer.BQConfig
            Specify configuration for interacting with BigQuery

        Returns
        -------
        pandas.DataFrame
            Output dataframe with the features per given point
        """

        # Load dataframe into bq with expiry
        dataset = bq.fetch_bq_dataset(client, dataset_id=bq_options.DATASET_ID)
        table_path = bq.upload_df_to_bq(
            df=df,
            client=client,
            dataset=dataset,
            expiry=bq_options.EXPIRY,
            max_retries=bq_options.MAX_RETRIES,
        )

        # Create query
        engine = create_engine(database_url)
        metadata = MetaData(bind=engine)

        source = Table(source_table, metadata, autoload=True)
        target = Table(table_path, metadata, autoload=True)

        pois = select(
            [source.c.osm_id, source.c.WKT], source.c.fclass == on
        ).cte("pois")
        distance = func.ST_Distance(
            func.ST_GeogFromText(target.c[column]), pois.c.WKT
        )
        pairs = (
            select([target, distance.label(feature_name)], distance < within)
            .select_from(pois)
            .cte("pairs")
        )
        partitioned = select(
            [
                pairs,
                func.row_number()
                .over(
                    partition_by=pairs.c["index"],
                    order_by=pairs.c[feature_name],
                )
                .label("row_number"),
            ]
        ).select_from(pairs)
        q = select(
            [
                literal_column(
                    "* EXCEPT (__index_level_0__, index, row_number)"
                )
            ],
            partitioned.c["row_number"] == 1,
        )

        # Perform query
        conn = engine.connect()
        results = conn.execute(q)

        return pd.DataFrame(list(results), columns=results.keys())
