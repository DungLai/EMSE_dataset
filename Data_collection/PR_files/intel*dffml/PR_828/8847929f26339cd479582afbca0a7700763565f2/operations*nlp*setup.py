import os
import importlib.util
from setuptools import setup

# Boilerplate to load commonalities
spec = importlib.util.spec_from_file_location(
    "setup_common", os.path.join(os.path.dirname(__file__), "setup_common.py")
)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

common.KWARGS["entry_points"] = {
    "dffml.operation": [
        f"remove_stopwords = {common.IMPORT_NAME}.operations:remove_stopwords",
        f"get_embedding = {common.IMPORT_NAME}.operations:get_embedding",
        f"pos_tagger = {common.IMPORT_NAME}.operations:pos_tagger",
        f"lemmatizer = {common.IMPORT_NAME}.operations:lemmatizer",
        f"get_similarity = {common.IMPORT_NAME}.operations:get_similarity",
        f"get_noun_chunks = {common.IMPORT_NAME}.operations:get_noun_chunks",
        f"get_sentences = {common.IMPORT_NAME}.operations:get_sentences",
        f"count_vectorizer = {common.IMPORT_NAME}.operations:count_vectorizer",
        f"tfidf_vectorizer = {common.IMPORT_NAME}.operations:tfidf_vectorizer",
        f"get_status_collected_data = {common.IMPORT_NAME}.operations:get_status_collected_data",
    ]
}

setup(**common.KWARGS)
