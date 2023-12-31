# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import concurrent.futures
import os

import hglib
from parsepatch.patch import Patch
from tqdm import tqdm

from bugbug import db

COMMITS_DB = 'data/commits.json'
db.register(COMMITS_DB, 'https://www.dropbox.com/s/mz3afgncx0siijc/commits.json.xz?dl=1')


def get_commits():
    return db.read(COMMITS_DB)


def _init(repo_dir):
    global HG
    HG = hglib.open(repo_dir)


def _transform(commit):
    desc = commit[5].decode('utf-8')

    bug_id = desc.split(' ')[1]

    obj = {
        # 'rev': commit[0].decode('utf-8'),
        # 'node': commit[1].decode('utf-8'),
        # 'tags': commit[2].decode('utf-8'),
        # 'branch': commit[3].decode('utf-8'),
        'author': commit[4].decode('utf-8'),
        'desc': desc,
        # 'date': str(commit[6]),
        'bug_id': bug_id,
        'added': 0,
        'deleted': 0,
        'files_modified_num': 0,
        'types': set(),
    }

    patch = HG.export(revs=[commit[1]], git=True)
    patch_data = Patch.parse_patch(patch.decode('utf-8', 'ignore'), skip_comments=False, add_lines_for_new=True)
    for path, stats in patch_data.items():
        if 'added' not in stats:
            # Must be a binary file
            obj['types'].add('binary')
            continue

        obj['added'] += len(stats['added']) + len(stats['touched'])
        obj['deleted'] += len(stats['deleted']) + len(stats['touched'])
        ext = os.path.splitext(path)[1]
        if ext in ['.js', '.jsm']:
            type_ = 'JavaScript'
        elif ext in ['.c', '.cpp', '.h']:
            type_ = 'C/C++'
        elif ext in ['.java']:
            type_ = 'Java'
        elif ext in ['.py']:
            type_ = 'Python'
        else:
            type_ = ext
        obj['types'].add(type_)

    obj['files_modified_num'] = len(patch_data)

    # Covert to a list, as a set is not JSON-serializable.
    obj['types'] = list(obj['types'])

    return obj


def download_commits(repo_dir):
    hg = hglib.open(repo_dir)

    commits = hg.log(keyword='Bug')
    commits_num = len(commits)

    hg.close()

    commits = (tuple(commit) for commit in commits)

    with concurrent.futures.ProcessPoolExecutor(initializer=_init, initargs=(repo_dir,)) as executor:
        commits = executor.map(_transform, commits, chunksize=256)
        commits = tqdm(commits, total=commits_num)
        db.write(COMMITS_DB, commits)


def get_commit_map():
    commit_map = {}

    for commit in get_commits():
        bug_id = commit['bug_id']

        if not bug_id:
            continue

        if bug_id not in commit_map:
            commit_map[bug_id] = []

        commit_map[bug_id].append(commit)

    return commit_map


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('repository_dir', help='Path to the repository', action='store')
    args = parser.parse_args()

    download_commits(args.repository_dir)
