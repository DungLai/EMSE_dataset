from spacy.language import Language
from spacy.tokenizer import Tokenizer
from spacy.util import compile_infix_regex, compile_prefix_regex, compile_suffix_regex
import re

#TODO I simply transferred my exploratory code - it is a mess and needs to be cleaned.

class SystematicReviewTokenizer():
    """
    A tokenizer for clinical text
    """
    def __init__(self, nlp):

        if not isinstance(nlp, Language):
            raise ValueError("NLP must be an instance of spacy.lang")
        self.nlp = nlp
        self.tokenizer = Tokenizer(nlp.vocab, nlp.Defaults.tokenizer_exceptions,
                                prefix_search=self._get_prefix_regex().search,
                                infix_finditer=self._get_infix_regex().finditer,
                                suffix_search=self._get_suffix_regex().search,
                                token_match=None
                     )

    def add_exceptions(self, exceptions):
        """
        Adds exception for tokenizer to ignore.
        :param exceptions: an array of terms to not split on during tokenization
        :return:
        """
        raise NotImplementedError()

    def _get_prefix_regex(self):
        """
        Custom prefix tokenization rules
        :return:
        """
        prefix = r"""^[\[\("'\\/@]"""
        all_prefixes_re = compile_prefix_regex(tuple(list(self.nlp.Defaults.prefixes) + [prefix]))
        return all_prefixes_re

    def _get_infix_regex(self):
        """
        Custom infix tokenization rules
        :return:
        """
        custom_infixes = [r'\[\]', r'(?<=[0-9])-(?=[0-9])', r'[!&:,()\*/-><]']
        infix_re = compile_infix_regex(tuple(list(self.nlp.Defaults.infixes) + custom_infixes))

        return infix_re

    def _get_suffix_regex(self):
        """
        Custom suffix tokenization rules
        :return:
        """
        suffix_re = re.compile(r'''[\]\)"',x\-%\?]$|(mg$)|(mcg$)|(mL$)|(cap$)|(\.$)''')
        return suffix_re
