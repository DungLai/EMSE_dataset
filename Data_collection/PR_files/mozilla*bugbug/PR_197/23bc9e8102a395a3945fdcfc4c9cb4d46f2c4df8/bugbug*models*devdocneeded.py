# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import xgboost
from imblearn.under_sampling import RandomUnderSampler
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline

from bugbug import bug_features
from bugbug import bugzilla
from bugbug.model import Model


class DevDocNeededModel(Model):
    def __init__(self, lemmatization=False):
        Model.__init__(self, lemmatization)

        self.sampler = RandomUnderSampler(random_state=0)

        feature_extractors = [
            bug_features.has_str(),
            bug_features.has_regression_range(),
            bug_features.severity(),
            bug_features.keywords({'dev-doc-needed', 'dev-doc-complete'}),
            bug_features.is_coverity_issue(),
            bug_features.has_crash_signature(),
            bug_features.has_url(),
            bug_features.has_w3c_url(),
            bug_features.has_github_url(),
            bug_features.whiteboard(),
            bug_features.patches(),
            bug_features.landings(),
            bug_features.title(),
            bug_features.product(),
            bug_features.component(),

            bug_features.commit_added(),
            bug_features.commit_deleted(),
            bug_features.commit_types(),
        ]

        cleanup_functions = [
            bug_features.cleanup_fileref,
            bug_features.cleanup_url,
            bug_features.cleanup_synonyms,
        ]

        self.extraction_pipeline = Pipeline([
            ('bug_extractor', bug_features.BugExtractor(feature_extractors, cleanup_functions, rollback=True, rollback_when=self.rollback, commit_data=True)),
            ('union', ColumnTransformer([
                ('data', DictVectorizer(), 'data'),

                ('title', self.text_vectorizer(), 'title'),

                ('comments', self.text_vectorizer(), 'comments'),
            ])),
        ])

        self.clf = xgboost.XGBClassifier(n_jobs=16)
        self.clf.set_params(predictor='cpu_predictor')

    def rollback(self, change):
        return change['field_name'] == 'keywords' and any(keyword in change['added'] for keyword in ['dev-doc-needed', 'dev-doc-complete'])

    def get_labels(self):
        classes = {}

        for bug_data in bugzilla.get_bugs():
            bug_id = int(bug_data['id'])

            for entry in bug_data['history']:
                for change in entry['changes']:
                    if change['field_name'] == 'keywords' and 'dev-doc-needed' in change['removed'] and 'dev-doc-complete' not in change['added']:
                        classes[bug_id] = 0
                        continue
                    if change['field_name'] == 'keywords' and any(keyword in change['added'] for keyword in ['dev-doc-needed', 'dev-doc-complete']):
                        classes[bug_id] = 1

            if bug_id not in classes:
                classes[bug_id] = 0

        return classes

    def get_feature_names(self):
        return self.extraction_pipeline.named_steps['union'].get_feature_names()
