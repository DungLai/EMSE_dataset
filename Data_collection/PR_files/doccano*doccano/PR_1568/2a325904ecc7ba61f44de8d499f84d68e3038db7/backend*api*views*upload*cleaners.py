from typing import List

from ...models import Project
from .label import CategoryLabel, Label, OffsetLabel


class Cleaner:

    def __init__(self, project: Project):
        pass

    def clean(self, labels: List[Label]) -> List[Label]:
        return labels


class SpanCleaner(Cleaner):

    def __init__(self, project: Project):
        super().__init__(project)
        self.allow_overlapping = getattr(project, 'allow_overlapping', False)

    def clean(self, labels: List[OffsetLabel]) -> List[OffsetLabel]:
        if self.allow_overlapping:
            return labels

        labels.sort(key=lambda label: label.start_offset)
        last_offset = -1
        new_labels = []
        for label in labels:
            if label.start_offset >= last_offset:
                last_offset = label.end_offset
                new_labels.append(label)
        return new_labels


class CategoryCleaner(Cleaner):

    def __init__(self, project: Project):
        super().__init__(project)
        self.exclusive = getattr(project, 'single_class_classification', False)

    def clean(self, labels: List[CategoryLabel]) -> List[CategoryLabel]:
        if self.exclusive:
            return labels[:1]
        else:
            return labels
