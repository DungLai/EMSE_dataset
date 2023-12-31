from ...models import (DOCUMENT_CLASSIFICATION, IMAGE_CLASSIFICATION, SEQ2SEQ,
                       SEQUENCE_LABELING, SPEECH2TEXT)
from . import catalog, cleaners, data, dataset, label, parsers


def get_data_class(project_type: str):
    text_projects = [DOCUMENT_CLASSIFICATION, SEQUENCE_LABELING, SEQ2SEQ]
    if project_type in text_projects:
        return data.TextData
    else:
        return data.FileData


def get_dataset_class(format: str):
    mapping = {
        catalog.TextFile.name: dataset.TextFileDataset,
        catalog.TextLine.name: dataset.TextLineDataset,
        catalog.CSV.name: dataset.CsvDataset,
        catalog.JSONL.name: dataset.JSONLDataset,
        catalog.JSON.name: dataset.JSONDataset,
        catalog.FastText.name: dataset.FastTextDataset,
        catalog.Excel.name: dataset.ExcelDataset,
        catalog.CoNLL.name: dataset.CoNLLDataset,
        catalog.ImageFile.name: dataset.FileBaseDataset,
        catalog.AudioFile.name: dataset.FileBaseDataset,
    }
    if format not in mapping:
        ValueError(f'Invalid format: {format}')
    return mapping[format]


def get_parser(file_format: str):
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
    return mapping[file_format]


def get_label_class(project_type: str):
    mapping = {
        DOCUMENT_CLASSIFICATION: label.CategoryLabel,
        SEQUENCE_LABELING: label.OffsetLabel,
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
