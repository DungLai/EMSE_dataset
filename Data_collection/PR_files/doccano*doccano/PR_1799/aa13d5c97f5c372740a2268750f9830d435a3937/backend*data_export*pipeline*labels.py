"""
Represents label collection.
"""
import abc
from collections import defaultdict
from typing import Dict, List

from django.db.models import QuerySet

from data_export.models import ExportedCategory, ExportedLabel
from examples.models import Example


class Labels(abc.ABC):
    label_class = ExportedLabel
    field_name = "labels"
    fields = ("example", "label")

    def __init__(self, examples: QuerySet[Example], user=None):
        self.label_groups = defaultdict(list)
        labels = self.label_class.objects.filter(example__in=examples)
        if user:
            labels = labels.filter(user=user)
        for label in labels.select_related(*self.fields):
            self.label_groups[label.example.id].append(label)

    def find_by(self, example_id: int) -> Dict[str, List[ExportedLabel]]:
        return {self.field_name: self.label_groups[example_id]}


class Categories(Labels):
    label_class = ExportedCategory
    field_name = "categories"
    fields = ("example", "label")
