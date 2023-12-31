import logging
import os

import pytest

from fonduer.parser.lingual_parser import SpacyParser
from fonduer.parser.models import Document
from fonduer.parser.parser import ParserUDF, SimpleParser
from fonduer.parser.preprocessors import (
    CSVDocPreprocessor,
    HTMLDocPreprocessor,
    TextDocPreprocessor,
    TSVDocPreprocessor,
)


def get_parser_udf(
    structural=True,  # structural information
    blacklist=["style", "script"],  # ignore tag types, default: style, script
    flatten=["span", "br"],  # flatten tag types, default: span, br
    language="en",
    lingual=True,  # lingual information
    lingual_parser=None,
    strip=True,
    replacements=[("[\u2010\u2011\u2012\u2013\u2014\u2212]", "-")],
    tabular=True,  # tabular information
    visual=False,  # visual information
    vizlink=None,
    pdf_path=None,
):
    """Return an instance of ParserUDF."""
    parser_udf = ParserUDF(
        structural=structural,
        blacklist=blacklist,
        flatten=flatten,
        lingual=lingual,
        lingual_parser=lingual_parser,
        strip=strip,
        replacements=replacements,
        tabular=tabular,
        visual=visual,
        vizlink=vizlink,
        pdf_path=pdf_path,
        language=language,
    )
    return parser_udf


def test_parse_md_details():
    """Test the parser with the md document."""
    logger = logging.getLogger(__name__)

    docs_path = "tests/data/html_simple/md.html"
    pdf_path = "tests/data/pdf_simple/md.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md"))

    # Check that doc has a name
    assert doc.name == "md"

    # Check that doc does not have any of these
    assert len(doc.figures) == 0
    assert len(doc.tables) == 0
    assert len(doc.cells) == 0
    assert len(doc.sentences) == 0

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True,
        tabular=True,
        lingual=True,
        visual=True,
        pdf_path=pdf_path,
        language="en",
    )
    doc = parser_udf.apply(doc)

    # Check that doc has a figure
    assert len(doc.figures) == 1
    assert doc.figures[0].url == "http://placebear.com/200/200"
    assert doc.figures[0].position == 0
    assert doc.figures[0].section.position == 0
    assert doc.figures[0].stable_id == "md::figure:0"

    #  Check that doc has a table
    assert len(doc.tables) == 1
    assert doc.tables[0].position == 0
    assert doc.tables[0].section.position == 0
    assert doc.tables[0].document.name == "md"

    # Check that doc has cells
    assert len(doc.cells) == 16
    cells = list(doc.cells)
    assert cells[0].row_start == 0
    assert cells[0].col_start == 0
    assert cells[0].position == 0
    assert cells[0].document.name == "md"
    assert cells[0].table.position == 0

    assert cells[10].row_start == 2
    assert cells[10].col_start == 2
    assert cells[10].position == 10
    assert cells[10].document.name == "md"
    assert cells[10].table.position == 0

    # Check that doc has sentences
    assert len(doc.sentences) == 45
    sent = sorted(doc.sentences, key=lambda x: x.position)[25]
    assert sent.text == "Spicy"
    assert sent.table.position == 0
    assert sent.table.section.position == 0
    assert sent.cell.row_start == 0
    assert sent.cell.col_start == 2

    # Check abs_char_offsets (#332)
    text = "".join([sent.text for sent in doc.sentences])
    for sent in doc.sentences:
        for abs_char_offset, word in zip(sent.abs_char_offsets, sent.words):
            assert text[abs_char_offset] == word[0]

    logger.info(f"Doc: {doc}")
    for i, sentence in enumerate(doc.sentences):
        logger.info(f"    Sentence[{i}]: {sentence.text}")

    header = sorted(doc.sentences, key=lambda x: x.position)[0]
    # Test structural attributes
    assert header.xpath == "/html/body/h1"
    assert header.html_tag == "h1"
    assert header.html_attrs == ["id=sample-markdown"]

    # Test visual attributes
    assert header.page == [1, 1]
    assert header.top == [35, 35]
    assert header.bottom == [61, 61]
    assert header.right == [111, 231]
    assert header.left == [35, 117]

    # Choose a sentence whose words get NER tags that are unlikely to change
    # even when a lang model changes.
    sent = sorted(doc.sentences, key=lambda x: x.position)[2]
    assert sent.words == ["Second", "Heading"]
    # Test lingual attributes
    assert sent.ner_tags[0] == "ORDINAL"
    assert sent.dep_labels[0] == "compound"

    # Test whether nlp information corresponds to sentence words
    for sent in doc.sentences:
        assert len(sent.words) == len(sent.lemmas)
        assert len(sent.words) == len(sent.pos_tags)
        assert len(sent.words) == len(sent.ner_tags)
        assert len(sent.words) == len(sent.dep_parents)
        assert len(sent.words) == len(sent.dep_labels)


def test_parse_wo_tabular():
    """Test the parser without extracting tabular information."""
    docs_path = "tests/data/html_simple/md.html"
    pdf_path = "tests/data/pdf_simple/md.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md"))

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True,
        tabular=False,
        lingual=True,
        visual=True,
        pdf_path=pdf_path,
        language="en",
    )
    doc = parser_udf.apply(doc)

    # Check that doc has neither table nor cell
    assert len(doc.sections) == 1
    assert len(doc.paragraphs) == 44
    assert len(doc.figures) == 1
    assert len(doc.tables) == 0
    assert len(doc.cells) == 0
    assert len(doc.sentences) == 45

    # Check that sentences are associated with both section and paragraph.
    assert all([sent.section is not None for sent in doc.sentences])
    assert all([sent.paragraph is not None for sent in doc.sentences])

    # Check that sentences are NOT associated with cell
    assert all([sent.cell is None for sent in doc.sentences])


@pytest.mark.skipif(
    "CI" not in os.environ, reason="Only run spacy non English test on GitHub Actions"
)
def test_spacy_german():
    """Test the parser with the md document."""
    docs_path = "tests/data/pure_html/brot.html"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md"))

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False, language="de"
    )
    doc = parser_udf.apply(doc)

    # Check that doc has sentences
    assert len(doc.sentences) == 841
    sent = sorted(doc.sentences, key=lambda x: x.position)[143]
    assert sent.ner_tags == [
        "O",
        "O",
        "LOC",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
        "O",
    ]  # inaccurate
    assert sent.dep_labels == [
        "mo",
        "ROOT",
        "sb",
        "mo",
        "nk",
        "nk",
        "punct",
        "mo",
        "nk",
        "nk",
        "nk",
        "sb",
        "oc",
        "rc",
        "punct",
    ]


@pytest.mark.skipif(
    "CI" not in os.environ, reason="Only run spacy non English test on GitHub Actions"
)
def test_spacy_japanese():
    """Test the parser with the md document."""
    # Test Japanese alpha tokenization
    docs_path = "tests/data/pure_html/japan.html"
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md"))
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False, language="ja"
    )
    doc = parser_udf.apply(doc)

    assert len(doc.sentences) == 289
    sent = doc.sentences[42]
    assert sent.text == "å½æãã«ã³ã»ãã¼ã­ãè¾¿ãçããã¨è¨ããã"
    assert sent.words == ["å½æ", "ãã«ã³", "ã»", "ãã¼ã­", "ã", "è¾¿ãçã", "ã", "ã¨", "è¨ã", "ãã"]
    assert sent.pos_tags == [
        "NOUN",
        "PROPN",
        "SYM",
        "PROPN",
        "ADP",
        "VERB",
        "AUX",
        "ADP",
        "VERB",
        "AUX",
    ]
    assert sent.lemmas == [
        "å½æ",
        "ãã«ã³-Marco",
        "ã»",
        "ãã¼ã­-Polo",
        "ã",
        "è¾¿ãçã",
        "ã",
        "ã¨",
        "è¨ã",
        "ãã",
    ]
    # Japanese sentences are only tokenized.
    assert sent.ner_tags == [""] * len(sent.words)
    assert sent.dep_labels == [""] * len(sent.words)


@pytest.mark.skipif(
    "CI" not in os.environ, reason="Only run spacy non English test on GitHub Actions"
)
def test_spacy_chinese():
    """Test the parser with the md document."""
    # Test Chinese alpha tokenization
    docs_path = "tests/data/pure_html/chinese.html"
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md"))
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False, language="zh"
    )
    doc = parser_udf.apply(doc)

    assert len(doc.sentences) == 8
    sent = doc.sentences[1]
    assert sent.text == "æä»¬åä»å¯¹æ¯è°æ´åå®³!"
    assert sent.words == ["æä»¬", "å", "ä»", "å¯¹æ¯", "è°", "æ´", "åå®³", "!"]
    # Chinese sentences are only tokenized.
    assert sent.ner_tags == ["", "", "", "", "", "", "", ""]
    assert sent.dep_labels == ["", "", "", "", "", "", "", ""]


def test_warning_on_missing_pdf():
    """Test that a warning is issued on invalid pdf."""
    docs_path = "tests/data/html_simple/md_para.html"
    pdf_path = "tests/data/pdf_simple/md_para_nonexistant.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md_para"))

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=True, pdf_path=pdf_path
    )
    with pytest.warns(RuntimeWarning) as record:
        doc = parser_udf.apply(doc)
    assert len(record) == 1
    assert "Visual parse failed" in record[0].message.args[0]


def test_warning_on_incorrect_filename():
    """Test that a warning is issued on invalid pdf."""
    docs_path = "tests/data/html_simple/md_para.html"
    pdf_path = "tests/data/html_simple/md_para.html"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md_para"))

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=True, pdf_path=pdf_path
    )
    with pytest.warns(RuntimeWarning) as record:
        doc = parser_udf.apply(doc)
    assert len(record) == 1
    assert "Visual parse failed" in record[0].message.args[0]


def test_parse_md_paragraphs():
    """Unit test of Paragraph parsing."""
    docs_path = "tests/data/html_simple/md_para.html"
    pdf_path = "tests/data/pdf_simple/md_para.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md_para"))

    # Check that doc has a name
    assert doc.name == "md_para"

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=True, pdf_path=pdf_path
    )
    doc = parser_udf.apply(doc)

    # Check that doc has a figure
    assert len(doc.figures) == 6
    assert doc.figures[0].url == "http://placebear.com/200/200"
    assert doc.figures[0].position == 0
    assert doc.figures[0].section.position == 0
    assert len(doc.figures[0].captions) == 0
    assert doc.figures[0].stable_id == "md_para::figure:0"
    assert doc.figures[0].cell.position == 13
    assert (
        doc.figures[2].url
        == "http://html5doctor.com/wp-content/uploads/2010/03/kookaburra.jpg"
    )
    assert doc.figures[2].position == 2
    assert len(doc.figures[2].captions) == 1
    assert len(doc.figures[2].captions[0].paragraphs[0].sentences) == 3
    assert (
        doc.figures[2].captions[0].paragraphs[0].sentences[0].text
        == "Australian Birds."
    )
    assert len(doc.figures[4].captions) == 0
    assert (
        doc.figures[4].url
        == "http://html5doctor.com/wp-content/uploads/2010/03/pelican.jpg"
    )

    #  Check that doc has a table
    assert len(doc.tables) == 1
    assert doc.tables[0].position == 0
    assert doc.tables[0].section.position == 0

    # Check that doc has cells
    assert len(doc.cells) == 16
    cells = list(doc.cells)
    assert cells[0].row_start == 0
    assert cells[0].col_start == 0
    assert cells[0].position == 0
    assert cells[0].table.position == 0

    assert cells[10].row_start == 2
    assert cells[10].col_start == 2
    assert cells[10].position == 10
    assert cells[10].table.position == 0

    # Check that doc has sentences
    assert len(doc.sentences) == 51
    sentences = sorted(doc.sentences, key=lambda x: x.position)
    sent1 = sentences[1]
    sent2 = sentences[2]
    sent3 = sentences[3]
    assert sent1.text == "This is some basic, sample markdown."
    assert sent2.text == (
        "Unlike the other markdown document, however, "
        "this document actually contains paragraphs of text."
    )
    assert sent1.paragraph.position == 1
    assert sent1.section.position == 0
    assert sent2.paragraph.position == 1
    assert sent2.section.position == 0
    assert sent3.paragraph.position == 1
    assert sent3.section.position == 0

    assert len(doc.paragraphs) == 46
    assert len(doc.paragraphs[1].sentences) == 3
    assert len(doc.paragraphs[2].sentences) == 1


def test_simple_parser():
    """Unit test of Parser on a single document with lingual features off."""
    logger = logging.getLogger(__name__)

    docs_path = "tests/data/html_simple/md.html"
    pdf_path = "tests/data/pdf_simple/md.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "md"))

    # Check that doc has a name
    assert doc.name == "md"

    # Create an Parser and parse the md document
    parser_udf = get_parser_udf(
        structural=True,
        lingual=False,
        visual=True,
        pdf_path=pdf_path,
        lingual_parser=SimpleParser(delim="NoDelim"),
    )
    doc = parser_udf.apply(doc)

    logger.info(f"Doc: {doc}")
    for i, sentence in enumerate(doc.sentences):
        logger.info(f"    Sentence[{i}]: {sentence.text}")

    header = sorted(doc.sentences, key=lambda x: x.position)[0]
    # Test structural attributes
    assert header.xpath == "/html/body/h1"
    assert header.html_tag == "h1"
    assert header.html_attrs == ["id=sample-markdown"]

    # Test lingual attributes
    assert header.ner_tags == ["", ""]
    assert header.dep_labels == ["", ""]
    assert header.dep_parents == [0, 0]
    assert header.lemmas == ["", ""]
    assert header.pos_tags == ["", ""]

    assert len(doc.sentences) == 44


def test_custom_parser():
    lingual_parser = SpacyParser("en")
    parser_udf = get_parser_udf(
        language="de", lingual=True, lingual_parser=lingual_parser
    )
    # The lingual_parser is prioritized over language
    assert parser_udf.lingual_parser == lingual_parser
    assert parser_udf.lingual_parser.lang == "en"


def test_parse_table_span():
    logger = logging.getLogger(__name__)

    docs_path = "tests/data/html_simple/table_span.html"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "table_span"))

    # Check that doc has a name
    assert doc.name == "table_span"

    # Create an Parser and parse the document
    parser_udf = get_parser_udf(structural=True, lingual=True, visual=False)
    doc = parser_udf.apply(doc)

    logger.info(f"Doc: {doc}")

    assert len(doc.sentences) == 1
    for sentence in doc.sentences:
        logger.info(f"    Sentence: {sentence.text}")


def test_parse_document_diseases():
    """Unit test of Parser on a single document.

    This tests both the structural and visual parse of the document.
    """
    logger = logging.getLogger(__name__)

    docs_path = "tests/data/html_simple/diseases.html"
    pdf_path = "tests/data/pdf_simple/diseases.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "diseases"))

    # Check that doc has a name
    assert doc.name == "diseases"

    # Create an Parser and parse the diseases document
    parser_udf = get_parser_udf(
        structural=True, lingual=True, visual=True, pdf_path=pdf_path
    )
    doc = parser_udf.apply(doc)

    logger.info(f"Doc: {doc}")
    for sentence in doc.sentences:
        logger.info(f"    Sentence: {sentence.text}")

    # Check captions
    assert len(doc.captions) == 2
    caption = sorted(doc.sentences, key=lambda x: x.position)[20]
    assert caption.paragraph.caption.position == 0
    assert caption.paragraph.caption.table.position == 0
    assert caption.text == "Table 1: Infectious diseases and where to find them."
    assert caption.paragraph.position == 18

    # Check figures
    assert len(doc.figures) == 0

    #  Check that doc has a table
    assert len(doc.tables) == 3
    assert doc.tables[0].position == 0
    assert doc.tables[0].document.name == "diseases"

    # Check that doc has cells
    assert len(doc.cells) == 25

    sentence = sorted(doc.sentences, key=lambda x: x.position)[10]
    logger.info(f"  {sentence}")

    # Check the sentence's cell
    assert sentence.table.position == 0
    assert sentence.cell.row_start == 2
    assert sentence.cell.col_start == 1
    assert sentence.cell.position == 4

    # Test structural attributes
    assert sentence.xpath == "/html/body/table[1]/tbody/tr[3]/td[1]/p"
    assert sentence.html_tag == "p"
    assert sentence.html_attrs == ["class=s6", "style=padding-top: 1pt"]

    # Test visual attributes
    assert sentence.page == [1, 1, 1]
    assert sentence.top == [342, 296, 356]
    assert sentence.left == [318, 369, 318]

    # Test lingual attributes
    assert sentence.ner_tags == ["O", "O", "GPE"]
    assert sentence.dep_labels == ["ROOT", "prep", "pobj"]

    assert len(doc.sentences) == 37


def test_parse_style():
    """Test style tag parsing."""
    logger = logging.getLogger(__name__)

    docs_path = "tests/data/html_extended/ext_diseases.html"
    pdf_path = "tests/data/pdf_extended/ext_diseases.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "ext_diseases"))

    # Create an Parser and parse the diseases document
    parser_udf = get_parser_udf(
        structural=True, lingual=True, visual=True, pdf_path=pdf_path
    )
    doc = parser_udf.apply(doc)

    # Grab the sentences parsed by the Parser
    sentences = doc.sentences

    logger.warning(f"Doc: {doc}")
    for i, sentence in enumerate(sentences):
        logger.warning(f"    Sentence[{i}]: {sentence.html_attrs}")

    # sentences for testing
    sub_sentences = [
        {
            "index": 6,
            "attr": [
                "class=col-header",
                "hobbies=work:hard;play:harder",
                "type=phenotype",
                "style=background: #f1f1f1; color: aquamarine; font-size: 18px;",
            ],
        },
        {"index": 9, "attr": ["class=row-header", "style=background: #f1f1f1;"]},
        {"index": 11, "attr": ["class=cell", "style=text-align: center;"]},
    ]

    # Assertions
    assert all(sentences[p["index"]].html_attrs == p["attr"] for p in sub_sentences)


def test_parse_error_doc_skipping():
    """Test skipping of faulty htmls."""
    faulty_doc_path = "tests/data/html_faulty/ext_diseases_missing_table_tag.html"
    preprocessor = HTMLDocPreprocessor(faulty_doc_path)
    doc = next(
        preprocessor._parse_file(faulty_doc_path, "ext_diseases_missing_table_tag")
    )
    parser_udf = get_parser_udf(structural=True, lingual=True)
    doc = parser_udf.apply(doc)
    # No document is returned for faulty document
    assert doc is None

    valid_doc_path = "tests/data/html_extended/ext_diseases.html"
    preprocessor = HTMLDocPreprocessor(valid_doc_path)
    doc = next(preprocessor._parse_file(valid_doc_path, "ext_diseases"))
    parser_udf = get_parser_udf(structural=True, lingual=True)
    doc = parser_udf.apply(doc)
    assert len(doc.sentences) == 37


def test_parse_multi_sections():
    """Test the parser with the radiology document."""
    # Test multi-section html
    docs_path = "tests/data/pure_html/radiology.html"
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "radiology"))
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False
    )
    doc = parser_udf.apply(doc)

    assert len(doc.sections) == 5
    assert len(doc.paragraphs) == 30
    assert len(doc.sentences) == 35
    assert len(doc.figures) == 2

    assert doc.sections[0].name is None
    assert doc.sections[1].name == "label"
    assert doc.sections[2].name == "content"
    assert doc.sections[3].name == "image"

    assert doc.sections[2].paragraphs[0].name == "COMPARISON"
    assert doc.sections[2].paragraphs[1].name == "INDICATION"
    assert doc.sections[2].paragraphs[2].name == "FINDINGS"
    assert doc.sections[2].paragraphs[3].name == "IMPRESSION"


def test_text_doc_preprocessor():
    """Test ``TextDocPreprocessor`` with text document."""
    # Test text document
    docs_path = "tests/data/various_format/text_format.txt"
    preprocessor = TextDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "plain_text_format"))
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False
    )
    doc = parser_udf.apply(doc)

    assert len(preprocessor) == 1
    assert len(doc.sections) == 1
    assert len(doc.paragraphs) == 1
    assert len(doc.sentences) == 57


def test_tsv_doc_preprocessor():
    """Test ``TSVDocPreprocessor`` with tsv document."""
    # Test tsv document
    docs_path = "tests/data/various_format/tsv_format.tsv"
    preprocessor = TSVDocPreprocessor(docs_path, header=True)

    assert len(preprocessor) == 2

    preprocessor = TSVDocPreprocessor(docs_path, max_docs=1, header=True)
    doc = next(preprocessor._parse_file(docs_path, "tsv_format"))
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False
    )
    doc = parser_udf.apply(doc)

    assert len(preprocessor) == 1
    assert doc.name == "9b28e780-ba48-4a53-8682-7c58c141a1b6"
    assert len(doc.sections) == 1
    assert len(doc.paragraphs) == 1
    assert len(doc.sentences) == 33


def test_csv_doc_preprocessor():
    """Test ``CSVDocPreprocessor`` with csv document."""
    # Test csv document
    docs_path = "tests/data/various_format/csv_format.csv"
    preprocessor = CSVDocPreprocessor(docs_path, header=True)

    assert len(preprocessor) == 10

    preprocessor = CSVDocPreprocessor(docs_path, max_docs=1, header=True)
    doc = next(preprocessor._parse_file(docs_path, "csv_format"))
    parser_udf = get_parser_udf(
        structural=True, tabular=True, lingual=True, visual=False
    )
    doc = parser_udf.apply(doc)

    assert len(preprocessor) == 1
    assert len(doc.sections) == 12
    assert len(doc.paragraphs) == 10
    assert len(doc.sentences) == 17


def test_parser_skips_and_flattens():
    """Test if ``Parser`` skips/flattens elements."""
    parser_udf = get_parser_udf()

    # Test if a parser skips comments
    doc = Document(id=1, name="test", stable_id="1::document:0:0")
    doc.text = "<html><body>Hello!<!-- comment --></body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "Hello!"

    # Test if a parser skips blacklisted elements
    doc = Document(id=2, name="test2", stable_id="2::document:0:0")
    doc.text = "<html><body><script>alert('Hello');</script><p>Hello!</p></body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "Hello!"

    # Test if a parser flattens elements
    doc = Document(id=3, name="test3", stable_id="3::document:0:0")
    doc.text = "<html><body><span>Hello, <br>world!</span></body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "Hello, world!"

    # Now with different blacklist and flatten
    parser_udf = get_parser_udf(blacklist=["meta"], flatten=["word"])

    # Test if a parser does not skip non-blacklisted element
    doc = Document(id=4, name="test4", stable_id="4::document:0:0")
    doc.text = "<html><body><script>alert('Hello');</script><p>Hello!</p></body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "alert('Hello');"
    assert doc.sentences[1].text == "Hello!"

    # Test if a parser skips blacklisted elements
    doc = Document(id=5, name="test5", stable_id="5::document:0:0")
    doc.text = "<html><head><meta name='keywords'></head><body>Hello!</body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "Hello!"

    # Test if a parser does not flatten elements
    doc = Document(id=6, name="test6", stable_id="6::document:0:0")
    doc.text = "<html><body><span>Hello, <br>world!</span></body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "Hello,"
    assert doc.sentences[1].text == "world!"

    # Test if a parser flattens elements
    doc = Document(id=7, name="test7", stable_id="7::document:0:0")
    doc.text = "<html><body><word>Hello, </word><word>world!</word></body></html>"
    doc = parser_udf.apply(doc)
    assert doc.sentences[0].text == "Hello, world!"


def test_parser_no_image():
    """Unit test of Parser on a single document that has a figure without image"""

    docs_path = "tests/data/html_simple/no_image.html"
    pdf_path = "tests/data/pdf_simple/no_image.pdf"

    # Preprocessor for the Docs
    preprocessor = HTMLDocPreprocessor(docs_path)
    doc = next(preprocessor._parse_file(docs_path, "no_image"))

    # Check that doc has a name
    assert doc.name == "no_image"

    # Create an Parser and parse the no_image document
    parser_udf = get_parser_udf(
        structural=True, lingual=False, visual=True, pdf_path=pdf_path,
    )
    doc = parser_udf.apply(doc)

    # Check that doc has no figures
    assert len(doc.figures) == 0
