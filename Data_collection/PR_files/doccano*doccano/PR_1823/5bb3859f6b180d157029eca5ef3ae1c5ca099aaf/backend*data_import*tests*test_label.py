import uuid
from unittest.mock import MagicMock

from django.test import TestCase
from model_mommy import mommy

from data_import.pipeline.label import (
    CategoryLabel,
    RelationLabel,
    SpanLabel,
    TextLabel,
)
from label_types.models import CategoryType, RelationType, SpanType
from labels.models import Category as CategoryModel
from labels.models import Relation as RelationModel
from labels.models import Span as SpanModel
from labels.models import TextLabel as TextModel
from projects.models import DOCUMENT_CLASSIFICATION, SEQ2SEQ, SEQUENCE_LABELING
from projects.tests.utils import prepare_project


class TestLabel(TestCase):
    task = "Any"

    def setUp(self):
        self.project = prepare_project(self.task)
        self.user = self.project.admin
        self.example = mommy.make("Example", project=self.project.item)


class TestCategoryLabel(TestLabel):
    task = DOCUMENT_CLASSIFICATION

    def test_comparison(self):
        category1 = CategoryLabel(label="A", example_uuid=uuid.uuid4())
        category2 = CategoryLabel(label="B", example_uuid=uuid.uuid4())
        self.assertLess(category1, category2)

    def test_empty_label_raises_value_error(self):
        with self.assertRaises(ValueError):
            CategoryLabel(label="", example_uuid=uuid.uuid4())

    def test_parse(self):
        example_uuid = uuid.uuid4()
        category = CategoryLabel.parse(example_uuid, obj="A")
        self.assertEqual(category.label, "A")
        self.assertEqual(category.example_uuid, example_uuid)

    def test_create_type(self):
        category = CategoryLabel(label="A", example_uuid=uuid.uuid4())
        category_type = category.create_type(self.project.item)
        self.assertIsInstance(category_type, CategoryType)
        self.assertEqual(category_type.text, "A")

    def test_create(self):
        category = CategoryLabel(label="A", example_uuid=uuid.uuid4())
        types = MagicMock()
        types.get_by_text.return_value = mommy.make(CategoryType, project=self.project.item)
        category_model = category.create(self.user, self.example, types)
        self.assertIsInstance(category_model, CategoryModel)


class TestSpanLabel(TestLabel):
    task = SEQUENCE_LABELING

    def test_comparison(self):
        span1 = SpanLabel(label="A", start_offset=0, end_offset=1, example_uuid=uuid.uuid4())
        span2 = SpanLabel(label="A", start_offset=1, end_offset=1, example_uuid=uuid.uuid4())
        self.assertLess(span1, span2)

    def test_parse_tuple(self):
        example_uuid = uuid.uuid4()
        span = SpanLabel.parse(example_uuid, obj=(0, 1, "A"))
        self.assertEqual(span.label, "A")
        self.assertEqual(span.start_offset, 0)
        self.assertEqual(span.end_offset, 1)

    def test_parse_dict(self):
        example_uuid = uuid.uuid4()
        span = SpanLabel.parse(example_uuid, obj={"label": "A", "start_offset": 0, "end_offset": 1})
        self.assertEqual(span.label, "A")
        self.assertEqual(span.start_offset, 0)
        self.assertEqual(span.end_offset, 1)

    def test_parse_invalid_dict(self):
        example_uuid = uuid.uuid4()
        span = SpanLabel.parse(example_uuid, obj={"label": "A", "start_offset": 0})
        self.assertEqual(span, None)

    def test_create_type(self):
        span = SpanLabel(label="A", start_offset=0, end_offset=1, example_uuid=uuid.uuid4())
        span_type = span.create_type(self.project.item)
        self.assertIsInstance(span_type, SpanType)
        self.assertEqual(span_type.text, "A")

    def test_create(self):
        span = SpanLabel(label="A", start_offset=0, end_offset=1, example_uuid=uuid.uuid4())
        types = MagicMock()
        types.get_by_text.return_value = mommy.make(SpanType, project=self.project.item)
        span_model = span.create(self.user, self.example, types)
        self.assertIsInstance(span_model, SpanModel)


class TestTextLabel(TestLabel):
    task = SEQ2SEQ

    def test_comparison(self):
        text1 = TextLabel(text="A", example_uuid=uuid.uuid4())
        text2 = TextLabel(text="B", example_uuid=uuid.uuid4())
        self.assertLess(text1, text2)

    def test_parse(self):
        example_uuid = uuid.uuid4()
        text = TextLabel.parse(example_uuid, obj="A")
        self.assertEqual(text.text, "A")

    def test_parse_invalid_data(self):
        example_uuid = uuid.uuid4()
        text = TextLabel.parse(example_uuid, obj=[])
        self.assertEqual(text, None)

    def test_create_type(self):
        text = TextLabel(text="A", example_uuid=uuid.uuid4())
        text_type = text.create_type(self.project.item)
        self.assertEqual(text_type, None)

    def test_create(self):
        text = TextLabel(text="A", example_uuid=uuid.uuid4())
        types = MagicMock()
        text_model = text.create(self.user, self.example, types)
        self.assertIsInstance(text_model, TextModel)


class TestRelationLabel(TestLabel):
    task = SEQUENCE_LABELING

    def test_comparison(self):
        relation1 = RelationLabel(type="A", from_id=0, to_id=1, example_uuid=uuid.uuid4())
        relation2 = RelationLabel(type="A", from_id=1, to_id=1, example_uuid=uuid.uuid4())
        self.assertLess(relation1, relation2)

    def test_parse(self):
        example_uuid = uuid.uuid4()
        relation = RelationLabel.parse(example_uuid, obj={"type": "A", "from_id": 0, "to_id": 1})
        self.assertEqual(relation.type, "A")
        self.assertEqual(relation.from_id, 0)
        self.assertEqual(relation.to_id, 1)

    def test_parse_invalid_data(self):
        example_uuid = uuid.uuid4()
        relation = RelationLabel.parse(example_uuid, obj={"type": "A", "from_id": 0})
        self.assertEqual(relation, None)

    def test_create_type(self):
        relation = RelationLabel(type="A", from_id=0, to_id=1, example_uuid=uuid.uuid4())
        relation_type = relation.create_type(self.project.item)
        self.assertIsInstance(relation_type, RelationType)
        self.assertEqual(relation_type.text, "A")

    def test_create(self):
        relation = RelationLabel(type="A", from_id=0, to_id=1, example_uuid=uuid.uuid4())
        types = MagicMock()
        types.get_by_text.return_value = mommy.make(RelationType, project=self.project.item)
        id_to_span = {
            0: mommy.make(SpanModel, start_offset=0, end_offset=1),
            1: mommy.make(SpanModel, start_offset=2, end_offset=3),
        }
        relation_model = relation.create(self.user, self.example, types, id_to_span=id_to_span)
        self.assertIsInstance(relation_model, RelationModel)
