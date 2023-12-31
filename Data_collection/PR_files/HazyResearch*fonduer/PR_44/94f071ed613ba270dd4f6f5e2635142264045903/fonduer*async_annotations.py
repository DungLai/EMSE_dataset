from __future__ import division

import codecs
import logging
import os
import subprocess
import tempfile
from builtins import range, str, zip
from collections import namedtuple

import numpy as np
import scipy.sparse as sparse
from pandas import DataFrame, Series

from fonduer.features.features import get_all_feats
from fonduer.models import Candidate, GoldLabel, GoldLabelKey, Marginal
from fonduer.models.meta import Meta, new_sessionmaker
from fonduer.udf import UDF, UDFRunner
from fonduer.utils import (matrix_conflicts, matrix_coverage, matrix_fn,
                           matrix_fp, matrix_overlaps, matrix_tn, matrix_tp,
                           remove_files)

# Used to conform to existing annotation key API call
# Note that this anontation matrix class can not be replaced with snorkel one
# since we do not have ORM-backed key objects but rather a simple python list.
_TempKey = namedtuple('TempKey', ['id', 'name'])

# Grab a pointer to the global vars
_meta = Meta.init()
logger = logging.getLogger(__name__)


def _to_annotation_generator(fns):
    """"
    Generic method which takes a set of functions, and returns a generator that yields
    function.__name__, function result pairs.
    """

    def fn_gen(c):
        for f in fns:
            yield f.__name__, f(c)

    return fn_gen


class csr_AnnotationMatrix(sparse.csr_matrix):
    """
    An extension of the scipy.sparse.csr_matrix class for holding sparse annotation matrices
    and related helper methods.
    """

    def __init__(self, arg1, **kwargs):
        # Note: Currently these need to return None if unset, otherwise matrix
        # copy operations break...
        # Map candidate id to row id
        self.candidate_index = kwargs.pop('candidate_index', {})
        # Map row id to candidate id
        self.row_index = kwargs.pop('row_index', [])
        # Map col id to key str
        self.keys = kwargs.pop('keys', [])
        # Map key str to col number
        self.key_index = kwargs.pop('key_index', {})

        # Note that scipy relies on the first three letters of the class to define matrix type...
        super(csr_AnnotationMatrix, self).__init__(arg1, **kwargs)

    def get_candidate(self, session, i):
        """Return the Candidate object corresponding to row i"""
        return session.query(Candidate).filter(
            Candidate.id == self.row_index[i]).one()

    def get_row_index(self, candidate):
        """Return the row index of the Candidate"""
        return self.candidate_index[candidate.id]

    def get_key(self, j):
        """Return the AnnotationKey object corresponding to column j"""
        return _TempKey(j, self.keys[j])

    def get_col_index(self, key):
        """Return the cow index of the AnnotationKey"""
        return self.key_index[key.id]

    def stats(self):
        """Return summary stats about the annotations"""
        raise NotImplementedError()

    def lf_stats(self, labels=None, est_accs=None):
        """Returns a pandas DataFrame with the LFs and various per-LF statistics"""
        lf_names = self.keys

        # Default LF stats
        col_names = ['j', 'Coverage', 'Overlaps', 'Conflicts']
        d = {
            'j': list(range(self.shape[1])),
            'Coverage': Series(data=matrix_coverage(self), index=lf_names),
            'Overlaps': Series(data=matrix_overlaps(self), index=lf_names),
            'Conflicts': Series(data=matrix_conflicts(self), index=lf_names)
        }
        if labels is not None:
            col_names.extend(['TP', 'FP', 'FN', 'TN', 'Empirical Acc.'])
            ls = np.ravel(labels.todense()
                          if sparse.issparse(labels) else labels)
            tp = matrix_tp(self, ls)
            fp = matrix_fp(self, ls)
            fn = matrix_fn(self, ls)
            tn = matrix_tn(self, ls)
            ac = (tp + tn) / (tp + tn + fp + fn)
            d['Empirical Acc.'] = Series(data=ac, index=lf_names)
            d['TP'] = Series(data=tp, index=lf_names)
            d['FP'] = Series(data=fp, index=lf_names)
            d['FN'] = Series(data=fn, index=lf_names)
            d['TN'] = Series(data=tn, index=lf_names)

        if est_accs is not None:
            col_names.append('Learned Acc.')
            d['Learned Acc.'] = Series(data=est_accs, index=lf_names)
        return DataFrame(data=d, index=lf_names)[col_names]


segment_dir = tempfile.gettempdir()


def get_sql_name(text):
    """
    Create valid SQL identifier as part of a feature storage table name
    """
    # Normalize identifier
    text = ''.join(c.lower() if c.isalnum() else ' ' for c in text)
    text = '_'.join(text.split())
    return text


def tsv_escape(s):
    if s is None:
        return '\\N'
    # Make sure feature names are still uniquely encoded in ascii
    s = str(s)
    s = s.replace('\"', '\\\\"').replace('\t', '\\t')
    if any(c in ',{}' for c in s):
        s = '"' + s + '"'
    return s


def array_tsv_escape(vals):
    return '{' + ','.join(tsv_escape(p) for p in vals) + '}'


def table_exists(con, name):
    cur = con.execute(
        "select exists(select * from information_schema.tables where table_name=%s)",
        (name, ))
    return cur.fetchone()[0]


def copy_postgres(segment_file_blob, table_name, tsv_columns):
    """
    @var segment_file_blob: e.g. "segment_*.tsv"
    @var table_name: The SQL table name to copy into
    @var tsv_columns: a string listing column names in the segment files
    separated by comma. e.g. "name, age, income"
    """
    logger.info('Copying {} to postgres'.format(table_name))

    username = "-U " + _meta.DBUSER if _meta.DBUSER is not None else ""
    password = "PGPASSWORD=" + _meta.DBPWD if _meta.DBPWD is not None else ""
    port = "-p " + str(_meta.DBPORT) if _meta.DBPORT is not None else ""
    cmd = ('cat %s | %s psql %s %s %s -c "COPY %s(%s) '
           'FROM STDIN" --set=ON_ERROR_STOP=true') % (segment_file_blob,
                                                      password, _meta.DBNAME,
                                                      username, port,
                                                      table_name, tsv_columns)
    _out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    logger.info(_out)


def _segment_filename(db_name, table_name, job_id, start=None, end=None):
    suffix = '*'
    if start is not None:
        suffix = str(start)
        if end is not None:
            suffix += '-' + str(end)
    return '%s_%s_%s_%s.tsv' % (db_name, table_name, job_id, suffix)


class BatchAnnotatorUDF(UDF):
    def __init__(self, f, **kwargs):
        self.anno_generator = _to_annotation_generator(f) if hasattr(
            f, '__iter__') else f
        super(BatchAnnotatorUDF, self).__init__(**kwargs)

    def apply(self, batch_range, table_name, split, cache, **kwargs):
        """
        Applies a given function to a range of candidates

        Note: Accepts a id_range as argument, because of issues with putting Candidate subclasses
        into Queues (can't pickle...)
        """
        start, end = batch_range
        file_name = _segment_filename(_meta.DBNAME, table_name, split,
                                      self.worker_id)
        segment_path = os.path.join(segment_dir, file_name)
        candidates = self.session.query(Candidate).filter(
            Candidate.split == split).order_by(Candidate.id).slice(start, end)
        with codecs.open(segment_path, 'a+', encoding='utf-8') as writer:
            if not cache:
                for i, candidate in enumerate(candidates):
                    # Runs the actual extraction function
                    nonzero_kvs = [(k, v)
                                   for k, v in self.anno_generator(candidate)
                                   if v != 0]
                    if nonzero_kvs:
                        keys, values = list(zip(*nonzero_kvs))
                    else:
                        keys = values = []
                    row = [
                        str(candidate.id),
                        array_tsv_escape(keys),
                        array_tsv_escape(values)
                    ]
                    writer.write('\t'.join(row) + '\n')
            else:
                nonzero_kv_dict = {}
                for id, k, v in self.anno_generator(list(candidates)):
                    if id not in nonzero_kv_dict:
                        nonzero_kv_dict[id] = []
                    if v != 0:
                        nonzero_kv_dict[id].append((k, v))
                for i, candidate in enumerate(candidates):
                    nonzero_kvs = nonzero_kv_dict[candidate.id]
                    if nonzero_kvs:
                        keys, values = list(zip(*nonzero_kvs))
                    else:
                        keys = values = []
                    row = [
                        str(candidate.id),
                        array_tsv_escape(keys),
                        array_tsv_escape(values)
                    ]
                    writer.write('\t'.join(row) + '\n')
        return
        yield


class BatchAnnotator(UDFRunner):
    """Abstract class for annotating candidates and persisting these annotations to DB"""

    def __init__(self,
                 candidate_type,
                 annotation_type,
                 f,
                 batch_size=50,
                 **kwargs):
        if isinstance(candidate_type, type):
            candidate_type = candidate_type.__name__
        self.table_name = get_sql_name(candidate_type) + '_' + annotation_type
        self.key_table_name = self.table_name + '_keys'
        self.annotation_type = annotation_type
        self.batch_size = batch_size
        super(BatchAnnotator, self).__init__(BatchAnnotatorUDF, f=f, **kwargs)

    def apply(self,
              split,
              key_group=0,
              replace_key_set=True,
              update_keys=False,
              update_values=True,
              storage=None,
              ignore_keys=[],
              **kwargs):
        if update_keys:
            replace_key_set = False
        # Get the cids based on the split, and also the count
        Session = new_sessionmaker()
        session = Session()
        # Note: In the current UDFRunner implementation, we load all these into memory and fill a
        # multiprocessing JoinableQueue with them before starting... so might as well load them here and pass in.
        # Also, if we try to pass in a query iterator instead, with AUTOCOMMIT on, we get a TXN error...
        candidates = session.query(Candidate).filter(
            Candidate.split == split).all()
        cids_count = len(candidates)
        if cids_count == 0:
            raise ValueError('No candidates in current split')

        # Setting up job batches
        chunks = cids_count // self.batch_size
        batch_range = [(i * self.batch_size, (i + 1) * self.batch_size)
                       for i in range(chunks)]
        remainder = cids_count % self.batch_size
        if remainder:
            batch_range.append((chunks * self.batch_size, cids_count))

        old_table_name = None
        table_name = self.table_name
        # Run the Annotator
        with _meta.engine.connect() as con:
            table_already_exists = table_exists(con, table_name)
            if update_values and table_already_exists:
                # Now we extract under a temporary name for merging
                old_table_name = table_name
                table_name += '_updates'

            segment_file_blob = os.path.join(segment_dir,
                                             _segment_filename(
                                                 _meta.DBNAME, self.table_name,
                                                 split))
            remove_files(segment_file_blob)
            cache = True if self.annotation_type == 'feature' else False
            super(BatchAnnotator, self).apply(
                batch_range,
                table_name=self.table_name,
                split=split,
                cache=cache,
                **kwargs)

            # Insert and update keys
            if not table_already_exists or old_table_name:
                con.execute(
                    'CREATE TABLE %s(candidate_id integer PRIMARY KEY, keys text[] NOT NULL, values real[] NOT NULL)'
                    % table_name)
            copy_postgres(segment_file_blob, table_name,
                          'candidate_id, keys, values')
            remove_files(segment_file_blob)

            # Replace the LIL table with COO if requested
            if storage == 'COO':
                temp_coo_table = table_name + '_COO'
                con.execute(
                    'CREATE TABLE %s AS '
                    '(SELECT candidate_id, UNNEST(keys) as key, UNNEST(values) as value from %s)'
                    % (temp_coo_table, table_name))
                con.execute('DROP TABLE %s' % table_name)
                con.execute('ALTER TABLE %s RENAME TO %s' % (temp_coo_table,
                                                             table_name))
                con.execute('ALTER TABLE %s ADD PRIMARY KEY(candidate_id, key)'
                            % table_name)
                # Update old table
                if old_table_name:
                    con.execute(
                        'INSERT INTO %s SELECT * FROM %s ON CONFLICT(candidate_id, key) '
                        'DO UPDATE SET value=EXCLUDED.value' % (old_table_name,
                                                                table_name))
                    con.execute('DROP TABLE %s' % table_name)
            else:  # LIL
                # Update old table
                if old_table_name:
                    con.execute(
                        'INSERT INTO %s AS old SELECT * FROM %s ON CONFLICT(candidate_id) '
                        'DO UPDATE SET '
                        'values=old.values || EXCLUDED.values,'
                        'keys=old.keys || EXCLUDED.keys' % (old_table_name,
                                                            table_name))
                    con.execute('DROP TABLE %s' % table_name)

            if old_table_name:
                table_name = old_table_name
            # Load the matrix
            key_table_name = self.key_table_name
            if key_group:
                key_table_name = self.key_table_name + '_' + get_sql_name(
                    key_group)

            return load_annotation_matrix(con, candidates, split, table_name,
                                          key_table_name, replace_key_set,
                                          storage, update_keys, ignore_keys)

    def clear(self, session, split, replace_key_set=False, **kwargs):
        """
        Deletes the Annotations for the Candidates in the given split.
        If replace_key_set=True, deletes *all* Annotations (of this Annotation sub-class)
        and also deletes all AnnotationKeys (of this sub-class)
        """
        with _meta.engine.connect() as con:
            if split is None:
                con.execute('DROP TABLE IF EXISTS %s' % self.table_name)
            elif table_exists(con, self.table_name):
                con.execute('DELETE FROM %s WHERE candidate_id IN '
                            '(SELECT id FROM candidate WHERE split=%d)' %
                            (self.table_name, split))
            if replace_key_set:
                con.execute('DROP TABLE IF EXISTS %s' % self.key_table_name)

    def apply_existing(self, split, key_group=0, **kwargs):
        """Alias for apply that emphasizes we are using an existing AnnotatorKey set."""
        return self.apply(
            split, key_group=key_group, replace_key_set=False, **kwargs)

    def load_matrix(self, split, ignore_keys=[]):
        Session = new_sessionmaker()
        session = Session()
        candidates = session.query(Candidate).filter(
            Candidate.split == split).all()
        with _meta.engine.connect() as con:
            return load_annotation_matrix(con, candidates, split,
                                          self.table_name, self.key_table_name,
                                          False, None, False, ignore_keys)


class BatchFeatureAnnotator(BatchAnnotator):
    def __init__(self, candidate_type, **kwargs):
        super(BatchFeatureAnnotator, self).__init__(
            candidate_type,
            annotation_type='feature',
            f=get_all_feats,
            **kwargs)


class BatchLabelAnnotator(BatchAnnotator):
    def __init__(self, candidate_type, lfs, label_generator=None, **kwargs):
        if lfs is not None:
            labels = lambda c: [(lf.__name__, lf(c)) for lf in lfs]
        elif label_generator is not None:
            labels = lambda c: label_generator(c)
        else:
            raise ValueError("Must provide lfs or label_generator kwarg.")

        # Convert lfs to a generator function
        # In particular, catch verbose values and convert to integer ones
        def f_gen(c):
            for lf_key, label in labels(c):
                # Note: We assume if the LF output is an int, it is already
                # mapped correctly
                if isinstance(label, int):
                    yield lf_key, label
                # None is a protected LF output value corresponding to 0,
                # representing LF abstaining
                elif label is None:
                    yield lf_key, 0
                elif label in c.values:
                    if c.cardinality > 2:
                        yield lf_key, c.values.index(label) + 1
                    # Note: Would be nice to not special-case here, but for
                    # consistency we leave binary LF range as {-1,0,1}
                    else:
                        val = 1 if c.values.index(label) == 0 else -1
                        yield lf_key, val
                else:
                    raise ValueError("""
                        Unable to parse label with value %s
                        for candidate with values %s""" % (label, c.values))

        super(BatchLabelAnnotator, self).__init__(
            candidate_type, annotation_type='label', f=f_gen, **kwargs)


def load_annotation_matrix(con, candidates, split, table_name, key_table_name,
                           replace_key_set, storage, update_keys, ignore_keys):
    """
    Loads a sparse matrix from an annotation table
    """
    if replace_key_set:
        # Recalculate unique keys for this set of candidates
        con.execute('DROP TABLE IF EXISTS %s' % key_table_name)
    if replace_key_set or not table_exists(con, key_table_name):
        if storage == 'COO':
            con.execute('CREATE TABLE %s AS '
                        '(SELECT DISTINCT key FROM %s)' % (key_table_name,
                                                           table_name))
        else:
            con.execute('CREATE TABLE %s AS '
                        '(SELECT DISTINCT UNNEST(keys) as key FROM %s)' %
                        (key_table_name, table_name))
        con.execute('ALTER TABLE %s ADD PRIMARY KEY(key)' % key_table_name)
    elif update_keys:
        if storage == 'COO':
            con.execute('INSERT INTO %s SELECT DISTINCT key FROM %s '
                        'ON CONFLICT(key) DO NOTHING' % (key_table_name,
                                                         table_name))
        else:
            con.execute(
                'INSERT INTO %s SELECT DISTINCT UNNEST(keys) as key FROM %s '
                'ON CONFLICT(key) DO NOTHING' % (key_table_name, table_name))

    # The result should be a list of all feature strings, small enough to hold in memory
    # TODO: store the actual index in table in case row number is unstable between queries
    ignore_keys = set(ignore_keys)
    keys = [
        row[0] for row in con.execute('SELECT * FROM %s' % key_table_name)
        if row[0] not in ignore_keys
    ]
    key_index = {key: i for i, key in enumerate(keys)}
    # Create sparse matrix in LIL format for incremental construction
    lil_feat_matrix = sparse.lil_matrix(
        (len(candidates), len(keys)), dtype=np.int64)

    row_index = []
    candidate_index = {}
    # Load annotations from database
    # TODO: move this for-loop computation to database for automatic parallelization,
    # avoid communication overhead etc. Try to avoid the log sorting factor using unnest
    if storage == 'COO':
        logger.info('key size: {}'.format(len(keys)))
        logger.info('candidate size {}'.format(len(candidates)))
        iterator_sql = 'SELECT candidate_id, key, value FROM %s '
        'WHERE candidate_id IN '
        '(SELECT id FROM candidate WHERE split=%d) '
        'ORDER BY candidate_id' % (table_name, split)
        prev_id = None
        i = -1
        for _, (candidate_id, key, value) in enumerate(
                con.execute(iterator_sql)):
            # Update candidate index tracker
            if candidate_id != prev_id:
                i += 1
                candidate_index[candidate_id] = i
                row_index.append(candidate_id)
                prev_id = candidate_id
            # Only keep known features
            key_id = key_index.get(key, None)
            if key_id is not None:
                lil_feat_matrix[i, key_id] = int(value)

    else:
        iterator_sql = '''SELECT candidate_id, keys, values FROM %s
                          WHERE candidate_id IN
                          (SELECT id FROM candidate WHERE split=%d)
                          ORDER BY candidate_id''' % (table_name, split)
        for i, (candidate_id, c_keys, values) in enumerate(
                con.execute(iterator_sql)):
            candidate_index[candidate_id] = i
            row_index.append(candidate_id)
            for key, value in zip(c_keys, values):
                # Only keep known features
                key_id = key_index.get(key, None)
                if key_id is not None:
                    lil_feat_matrix[i, key_id] = int(value)

    return csr_AnnotationMatrix(
        lil_feat_matrix,
        candidate_index=candidate_index,
        row_index=row_index,
        keys=keys,
        key_index=key_index)


class csr_LabelMatrix(csr_AnnotationMatrix):
    def lf_stats(self, session, labels=None, est_accs=None):
        """Returns a pandas DataFrame with the LFs and various per-LF statistics"""
        lf_names = [
            self.get_key(session, j).name for j in range(self.shape[1])
        ]

        # Default LF stats
        col_names = ['j', 'Coverage', 'Overlaps', 'Conflicts']
        d = {
            'j': list(range(self.shape[1])),
            'Coverage': Series(data=matrix_coverage(self), index=lf_names),
            'Overlaps': Series(data=matrix_overlaps(self), index=lf_names),
            'Conflicts': Series(data=matrix_conflicts(self), index=lf_names)
        }
        if labels is not None:
            col_names.extend(['TP', 'FP', 'FN', 'TN', 'Empirical Acc.'])
            ls = np.ravel(labels.todense()
                          if sparse.issparse(labels) else labels)
            tp = matrix_tp(self, ls)
            fp = matrix_fp(self, ls)
            fn = matrix_fn(self, ls)
            tn = matrix_tn(self, ls)
            ac = (tp + tn) / (tp + tn + fp + fn)
            d['Empirical Acc.'] = Series(data=ac, index=lf_names)
            d['TP'] = Series(data=tp, index=lf_names)
            d['FP'] = Series(data=fp, index=lf_names)
            d['FN'] = Series(data=fn, index=lf_names)
            d['TN'] = Series(data=tn, index=lf_names)

        if est_accs is not None:
            col_names.append('Learned Acc.')
            d['Learned Acc.'] = est_accs
            d['Learned Acc.'].index = lf_names
        return DataFrame(data=d, index=lf_names)[col_names]


def load_matrix(matrix_class,
                annotation_key_class,
                annotation_class,
                session,
                split=0,
                cids_query=None,
                key_group=0,
                key_names=None,
                zero_one=False,
                load_as_array=False):
    """
    Returns the annotations corresponding to a split of candidates with N members
    and an AnnotationKey group with M distinct keys as an N x M CSR sparse matrix.
    """
    cid_query = cids_query or session.query(Candidate.id)\
                                     .filter(Candidate.split == split)
    cid_query = cid_query.order_by(Candidate.id)

    keys_query = session.query(annotation_key_class.id)
    keys_query = keys_query.filter(annotation_key_class.group == key_group)
    if key_names is not None:
        keys_query = keys_query.filter(
            annotation_key_class.name.in_(frozenset(key_names)))
    keys_query = keys_query.order_by(annotation_key_class.id)

    # First, we query to construct the row index map
    cid_to_row = {}
    row_to_cid = {}
    for cid, in cid_query.all():
        if cid not in cid_to_row:
            j = len(cid_to_row)

            # Create both mappings
            cid_to_row[cid] = j
            row_to_cid[j] = cid

    # Second, we query to construct the column index map
    kid_to_col = {}
    col_to_kid = {}
    for kid, in keys_query.all():
        if kid not in kid_to_col:
            j = len(kid_to_col)

            # Create both mappings
            kid_to_col[kid] = j
            col_to_kid[j] = kid

    # Create sparse matrix in COO format for incremental construction
    row = []
    columns = []
    data = []

    # Rely on the core for fast iteration
    annot_select_query = annotation_class.__table__.select()

    # Iteratively construct row index and output sparse matrix
    # Cycles through the entire table to load the data.
    # Performance may slow down based on table size; however, negligible since
    # it takes 8min to go throuh 245M rows (pretty fast).
    for res in session.execute(annot_select_query):
        # NOTE: The order of return seems to be switched in Python 3???
        # Either way, make sure the order is set here explicitly!
        cid, kid, val = res.candidate_id, res.key_id, res.value

        if cid in cid_to_row and kid in kid_to_col:

            # Optionally restricts val range to {0,1}, mapping -1 -> 0
            if zero_one:
                val = 1 if val == 1 else 0
            row.append(cid_to_row[cid])
            columns.append(kid_to_col[kid])
            data.append(int(val))

    X = sparse.coo_matrix(
        (data, (row, columns)), shape=(len(cid_to_row), len(kid_to_col)))

    # Return as an AnnotationMatrix
    Xr = matrix_class(
        X,
        candidate_index=cid_to_row,
        row_index=row_to_cid,
        annotation_key_cls=annotation_key_class,
        key_index=kid_to_col,
        col_index=col_to_kid)
    return np.squeeze(Xr.toarray()) if load_as_array else Xr


def load_gold_labels(session, annotator_name, **kwargs):
    return load_matrix(
        csr_LabelMatrix,
        GoldLabelKey,
        GoldLabel,
        session,
        key_names=[annotator_name],
        **kwargs)


def save_marginals(session, X, marginals, training=True):
    """Save marginal probabilities for a set of Candidates to db.

    :param X: Either an M x N csr_AnnotationMatrix-class matrix, where M
        is number of candidates, N number of LFs/features; OR a list of
        arbitrary objects with candidate ids accessible via a .id attrib
    :param marginals: A dense M x K matrix of marginal probabilities, where
        K is the cardinality of the candidates, OR a M-dim list/array if K=2.
    :param training: If True, these are training marginals / labels; else they
        are saved as end model predictions.

    Note: The marginals for k=0 are not stored, only for k = 1,...,K
    """
    logger = logging.getLogger(__name__)
    # Make sure that we are working with a numpy array
    try:
        shape = marginals.shape
    except Exception as e:
        marginals = np.array(marginals)
        shape = marginals.shape

    # Handle binary input as M x 1-dim array; assume elements represent
    # poksitive (k=1) class values
    if len(shape) == 1:
        marginals = np.vstack([1 - marginals, marginals]).T

    # Only add values for classes k=1,...,K
    marginal_tuples = []
    for i in range(shape[0]):
        for k in range(1, shape[1] if len(shape) > 1 else 2):
            if marginals[i, k] > 0:
                marginal_tuples.append((i, k, marginals[i, k]))

    # NOTE: This will delete all existing marginals of type `training`
    session.query(Marginal).filter(Marginal.training == training).\
        delete(synchronize_session='fetch')

    # Prepare bulk INSERT query
    q = Marginal.__table__.insert()

    # Check whether X is an AnnotationMatrix or not
    anno_matrix = isinstance(X, csr_AnnotationMatrix)
    if not anno_matrix:
        X = list(X)

    # Prepare values
    insert_vals = []
    for i, k, p in marginal_tuples:
        cid = X.get_candidate(session, i).id if anno_matrix else X[i].id
        insert_vals.append({
            'candidate_id': cid,
            'training': training,
            'value': k,
            # We cast p in case its a numpy type, which psycopg2 does not handle
            'probability': float(p)
        })

    # Execute update
    session.execute(q, insert_vals)
    session.commit()
    logger.info("Saved {%d} marginals".format(len(marginals)))


# TODO(senwu): Check to see if we can inherit from BatchFeatureAnnotator
#  class COOFeatureAnnotator(BatchFeatureAnnotator):
#      def __init__(self, f=get_all_feats, **kwargs):
#          super(COOFeatureAnnotator, f, **kwargs)
