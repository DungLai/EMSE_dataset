from typing import Any, Dict, Iterator, List

import pandas as pd
from django.db.models.query import QuerySet

from .labels import Labels
from data_export.models import ExportedExample


class Dataset:
    def __init__(self, examples: QuerySet[ExportedExample], labels: List[Labels]):
        self.examples = examples
        self.labels = labels

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        for example in self.examples:
            data = example.to_dict()
            for labels in self.labels:
                data.update(**labels.find_by(example.id))
            yield data

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self)
