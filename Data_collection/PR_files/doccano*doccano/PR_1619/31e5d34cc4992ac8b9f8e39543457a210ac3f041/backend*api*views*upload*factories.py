from ...models import (DOCUMENT_CLASSIFICATION, IMAGE_CLASSIFICATION, SEQ2SEQ,
                       SEQUENCE_LABELING, SPEECH2TEXT)
from . import builders, catalog, cleaners, data, label, parsers, readers


def get_data_class(project_type: str):
    text_projects = [DOCUMENT_CLASSIFICATION, SEQUENCE_LABELING, SEQ2SEQ]
    if project_type in text_projects:
        return data.TextData
    else:
        return data.FileData


def create_parser(file_format: str, **kwargs):
    mapping = {
        catalog.TextFile.name: parsers.TextFileParser,
        catalog.TextLine.name: parsers.LineParser,
        catalog.CSV.name: parsers.CSVParser,
        catalog.JSONL.name: parsers.JSONLParser,
        catalog.JSON.name: parsers.JSONParser,
        catalog.FastText.name: parsers.FastTextParser,
        catalog.Excel.name: parsers.ExcelParser,
        catalog.CoNLL.name: parsers.CoNLLParser,
        catalog.ImageFile.name: parsers.PlainParser,
        catalog.AudioFile.name: parsers.PlainParser,
    }
    if file_format not in mapping:
        raise ValueError(f'Invalid format: {file_format}')
    return mapping[file_format](**kwargs)


def get_label_class(project_type: str):
    mapping = {
        DOCUMENT_CLASSIFICATION: label.CategoryLabel,
        SEQUENCE_LABELING: label.SpanLabel,
        SEQ2SEQ: label.TextLabel,
        IMAGE_CLASSIFICATION: label.CategoryLabel,
        SPEECH2TEXT: label.TextLabel,
    }
    if project_type not in mapping:
        ValueError(f'Invalid project type: {project_type}')
    return mapping[project_type]


def create_cleaner(project):
    mapping = {
        DOCUMENT_CLASSIFICATION: cleaners.CategoryCleaner,
        SEQUENCE_LABELING: cleaners.SpanCleaner,
        IMAGE_CLASSIFICATION: cleaners.CategoryCleaner
    }
    if project.project_type not in mapping:
        ValueError(f'Invalid project type: {project.project_type}')
    cleaner_class = mapping.get(project.project_type, cleaners.Cleaner)
    return cleaner_class(project)


def create_bulder(project, **kwargs):
    data_column = builders.DataColumn(
        name=kwargs.get('column_data', readers.DEFAULT_TEXT_COLUMN),
        value_class=get_data_class(project.project_type)
    )
    # Todo: If project is EntityClassification,
    # column names are fixed: entities, cats
    label_column = builders.LabelColumn(
        name=kwargs.get('column_label', readers.DEFAULT_LABEL_COLUMN),
        value_class=get_label_class(project.project_type)
    )
    builder = builders.ColumnBuilder(
        data_column=data_column,
        label_columns=[label_column]
    )
    return builder
