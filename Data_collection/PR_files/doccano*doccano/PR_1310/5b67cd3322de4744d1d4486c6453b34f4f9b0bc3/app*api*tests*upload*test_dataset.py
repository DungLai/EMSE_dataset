import os
import shutil
import tempfile
import unittest

from ...views.upload.dataset import Dataset
from ...views.upload.label import Label


class TestDataset(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'test_file.txt')
        self.content = 'ããã«ã¡ã¯ãä¸çï¼'

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, encoding=None):
        with open(self.test_file, 'w', encoding=encoding) as f:
            f.write(self.content)

    def test_can_load_utf8(self):
        self.create_file()
        dataset = Dataset(filenames=[], label_class=Label)
        record = next(dataset.load(self.test_file))
        self.assertEqual(record.filename, self.test_file)

    def test_cannot_load_shiftjis_without_specifying_encoding(self):
        self.create_file('shift_jis')
        dataset = Dataset(filenames=[], label_class=Label)
        with self.assertRaises(UnicodeDecodeError):
            next(dataset.load(self.test_file))

    def test_can_load_shiftjis_with_specifying_encoding(self):
        self.create_file('shift_jis')
        dataset = Dataset(filenames=[], label_class=Label, encoding='shift_jis')
        record = next(dataset.load(self.test_file))
        self.assertEqual(record.filename, self.test_file)
