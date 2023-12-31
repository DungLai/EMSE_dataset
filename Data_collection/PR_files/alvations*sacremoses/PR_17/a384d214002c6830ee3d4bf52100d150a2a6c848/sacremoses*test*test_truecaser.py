# -*- coding: utf-8 -*-

"""
Tests for MosesTokenizer
"""

import io
import os
import unittest

from six import text_type

from sacremoses.truecase import MosesTruecaser, MosesDetruecaser


# Crazy hack to support Python2 and 3 and requests to download files.
# From https://stackoverflow.com/a/47897956/610569
try: # Try importing Python3 urllib
    import urllib.request
except ImportError: # Now importing Python2 urllib
    import urllib


def get_content(url):
    try: # Using Python3 urllib.
        with urllib.request.urlopen(url) as response:
            return response.read() # Returns http.client.HTTPResponse.
    except AttributeError: # Using Python3 urllib.
        return urllib.urlopen(url).read() # Returns an instance.


class TestTruecaser(unittest.TestCase):
    def test_moses_truecase_documents(self):
        moses = MosesTruecaser()
        # Train the model from documents.
        docs = [line.split() for line in self.big_txt.split('\n')]
        moses.train(docs)
        # Test all self.input_output test cases.
        for _input, _output in self.input_output.items():
            truecased = moses.truecase(_input)
            assert truecased == _output

    def test_moses_truecase_file(self):
        moses = MosesTruecaser()
        # Train the model from file.
        moses.train_from_file('big.txt')
        # Test all self.input_output test cases.
        for _input, _output in self.input_output.items():
            assert moses.truecase(_input) == _output

    # def test_train_from_file(self):
    #     moses = MosesTruecaser()
    #     # Train the model from file.
    #     moses.train_from_file('corpus.de')

    # def test_german_corpus(self):
    #     moses = MosesTruecaser('de.truecasemodel')
    #
    #     with io.open('corpus.de', encoding='utf-8') as corpus, io.open('corpus.truecased.de', encoding='utf-8') as truecased_corpus:
    #         for original, truecased_reference in zip(corpus, truecased_corpus):
    #             truecased_reference = truecased_reference.rstrip()
    #             original = original.rstrip()
    #
    #             truecased_ported = moses.truecase(original, return_str=True)
    #
    #             assert truecased_ported == truecased_reference

    def setUp(self):
        # Check if the Norvig's big.txt file exists.
        if os.path.isfile('big.txt'):
            with open('big.txt') as fin:
                self.big_txt = fin.read()
        else: # Otherwise, download the big.txt.
            self.big_txt = get_content("https://norvig.com/big.txt").decode('utf8')
            with open('big.txt', 'w') as fout:
                fout.write(self.big_txt)

        # Test case where inputs are all caps.
        caps_input = "THE ADVENTURES OF SHERLOCK HOLMES"

        # actual output of truecase.perl, when trained on big.txt:
        # perl train - truecaser.perl --model big.model --corpus big.txt
        # echo "THE ADVENTURES OF SHERLOCK HOLMES" | perl truecase.perl --model big.model
        # the ADVENTURES OF SHERLOCK HOLMES
        expected_caps_output = ['the', 'ADVENTURES', 'OF', 'SHERLOCK', 'HOLMES']

        # Test normal input to truecase.
        normal_input = str('You can also find out about how to make a donation '
                           'to Project Gutenberg, and how to get involved.')
        expected_normal_output = ['you', 'can', 'also', 'find', 'out', 'about',
                                'how', 'to', 'make', 'a', 'donation', 'to',
                                'Project', 'Gutenberg,', 'and', 'how', 'to',
                                'get', 'involved.']

        second_cased_token_input = 'Rustic elegance can be found at Alaska Heavenly Lodge.'

        # lodge should not be lowercased, because it was seen both upper and lowercase in the training material.
        # heavenly was just seen lowercase in the training material, therefore it should be lowercase.
        expected_second_cased_token_output = 'rustic elegance can be found at Alaska heavenly Lodge.'.split()

        # Keep a key-value pairs of in/outputs.
        self.input_output = {caps_input: expected_caps_output,
                             normal_input: expected_normal_output,
                             second_cased_token_input: expected_second_cased_token_output}


class TestDetruecaser(unittest.TestCase):
    def test_moses_detruecase_str(self):
        moses = MosesDetruecaser()
        text = 'the adventures of Sherlock Holmes'
        expected = ['The', 'adventures', 'of', 'Sherlock', 'Holmes']
        expected_str = 'The adventures of Sherlock Holmes'
        assert moses.detruecase(text) == expected
        assert moses.detruecase(text, return_str=True) == expected_str

    def test_moses_detruecase_headline(self):
        moses = MosesDetruecaser()
        text = 'the adventures of Sherlock Holmes'
        expected = ['The', 'Adventures', 'of', 'Sherlock', 'Holmes']
        expected_str = 'The Adventures of Sherlock Holmes'
        assert moses.detruecase(text, is_headline=True) == expected
        assert moses.detruecase(text, is_headline=True, return_str=True) == expected_str

    def test_moses_detruecase_file(self):
        moses = MosesDetruecaser()
        text = text_type('the adventures of Sherlock Holmes\n'
                        '<hl> something ABC has gone wrong Xyz , \n'
                        'second line of HEADERS that are very Importante .\n'
                        '</hl>\n'
                        'then the next sentence with Caps here and There .\n'
                      )

        with io.open('detruecase-test.txt', 'w', encoding='utf8') as fout:
            with io.StringIO(text) as fin:
                fout.write(fin.read())

        expected = ['The adventures of Sherlock Holmes',
                    '<hl> Something Abc Has Gone Wrong Xyz ,',
                    'Second Line of Headers That Are Very Importante .', '</hl>',
                    'Then the next sentence with Caps here and There .']

        assert list(moses.detruecase_file('detruecase-test.txt')) == expected
