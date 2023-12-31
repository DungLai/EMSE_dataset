# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import collections
import math
import pickle
import statistics
from functools import reduce
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
import xgboost
from imblearn.under_sampling import RandomUnderSampler
from ortools.linear_solver import pywraplp
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline
from tqdm import tqdm

from bugbug import (
    commit_features,
    repository,
    test_scheduling,
    test_scheduling_features,
    utils,
)
from bugbug.model import Model


def get_commit_map():
    commit_map = {}

    for commit in repository.get_commits():
        commit_map[commit["node"]] = commit

    assert len(commit_map) > 0
    return commit_map


class TestSelectModel(Model):
    def __init__(self, lemmatization=False, granularity="label", failures_skip=None):
        Model.__init__(self, lemmatization)

        self.granularity = granularity
        self.failures_skip = failures_skip

        self.training_dbs = [repository.COMMITS_DB]
        self.eval_dbs[repository.COMMITS_DB] = (
            repository.COMMITS_DB,
            repository.COMMIT_EXPERIENCES_DB,
        )
        if granularity == "label":
            self.training_dbs.append(test_scheduling.TEST_LABEL_SCHEDULING_DB)
            self.eval_dbs[test_scheduling.TEST_LABEL_SCHEDULING_DB] = (
                test_scheduling.PAST_FAILURES_LABEL_DB,
                test_scheduling.FAILING_TOGETHER_LABEL_DB,
            )
        elif granularity == "group":
            self.training_dbs.append(test_scheduling.TEST_GROUP_SCHEDULING_DB)
            self.eval_dbs[test_scheduling.TEST_GROUP_SCHEDULING_DB] = (
                test_scheduling.PAST_FAILURES_GROUP_DB,
                test_scheduling.TOUCHED_TOGETHER_DB,
                test_scheduling.FAILING_TOGETHER_CONFIG_GROUP_DB,
            )
        elif granularity == "config_group":
            self.training_dbs.append(test_scheduling.TEST_CONFIG_GROUP_SCHEDULING_DB)
            self.eval_dbs[test_scheduling.TEST_CONFIG_GROUP_SCHEDULING_DB] = (
                test_scheduling.PAST_FAILURES_CONFIG_GROUP_DB,
                test_scheduling.TOUCHED_TOGETHER_DB,
            )

        self.cross_validation_enabled = False

        self.entire_dataset_training = True

        self.sampler = RandomUnderSampler(random_state=0)

        feature_extractors = [
            test_scheduling_features.prev_failures(),
        ]

        if granularity == "label":
            feature_extractors += [
                test_scheduling_features.platform(),
                # test_scheduling_features.chunk(),
                test_scheduling_features.suite(),
            ]
        elif granularity in ("group", "config_group"):
            feature_extractors += [
                test_scheduling_features.path_distance(),
                test_scheduling_features.common_path_components(),
                test_scheduling_features.touched_together(),
            ]

        self.extraction_pipeline = Pipeline(
            [
                (
                    "commit_extractor",
                    commit_features.CommitExtractor(feature_extractors, []),
                ),
                ("union", ColumnTransformer([("data", DictVectorizer(), "data")])),
            ]
        )

        self.clf = xgboost.XGBClassifier(n_jobs=utils.get_physical_cpu_count())
        self.clf.set_params(predictor="cpu_predictor")

    def get_pushes(
        self, apply_filters: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        pushes = []
        for revs, test_datas in test_scheduling.get_test_scheduling_history(
            self.granularity
        ):
            failures = []
            passes = []

            for test_data in test_datas:
                name = test_data["name"]

                if self.granularity == "label" and not name.startswith("test-"):
                    continue

                if (
                    test_data["is_likely_regression"]
                    or test_data["is_possible_regression"]
                ):
                    failures.append(name)
                else:
                    passes.append(name)

            if apply_filters:
                if self.failures_skip and len(failures) > self.failures_skip:
                    continue

            pushes.append(
                {"revs": revs, "failures": failures, "passes": passes,}
            )

        return pushes, math.floor(0.9 * len(pushes))

    # To properly test the performance of our model, we need to split the data
    # according to time: we train on older pushes and evaluate on newer pushes.
    def train_test_split(self, X, y):
        pushes, train_push_len = self.get_pushes(True)
        train_len = sum(
            len(push["failures"]) + len(push["passes"])
            for push in pushes[:train_push_len]
        )
        print(
            f"{train_push_len} pushes in the training set (corresponding to {train_len} push/jobs)"
        )
        return X[:train_len], X[train_len:], y[:train_len], y[train_len:]

    def items_gen(self, classes):
        commit_map = get_commit_map()

        for revs, test_datas in test_scheduling.get_test_scheduling_history(
            self.granularity
        ):
            commits = tuple(
                commit_map[revision] for revision in revs if revision in commit_map
            )
            if len(commits) == 0:
                continue

            for test_data in test_datas:
                name = test_data["name"]

                if (revs[0], name) not in classes:
                    continue

                commit_data = commit_features.merge_commits(commits)
                commit_data["test_job"] = test_data
                yield commit_data, classes[(revs[0], name)]

    def get_labels(self):
        classes = {}
        pushes, _ = self.get_pushes(True)

        for push in pushes:
            for name in push["failures"]:
                classes[(push["revs"][0], name)] = 1

            for name in push["passes"]:
                classes[(push["revs"][0], name)] = 0

        print("{} pushes considered".format(len(pushes)))
        print(
            "{} pushes with at least one failure".format(
                sum(1 for push in pushes if len(push["failures"]) > 0)
            )
        )
        print(
            "{} push/jobs failed".format(
                sum(1 for label in classes.values() if label == 1)
            )
        )
        print(
            "{} push/jobs did not fail".format(
                sum(1 for label in classes.values() if label == 0)
            )
        )

        return classes, [0, 1]

    def select_tests(
        self,
        commits: Iterable[dict],
        confidence: float = 0.5,
        push_num: Optional[int] = None,
    ) -> Dict[str, float]:
        commit_data = commit_features.merge_commits(commits)

        past_failures_data = test_scheduling.get_past_failures(self.granularity)

        if push_num is None:
            push_num = past_failures_data["push_num"] + 1
        all_runnables = past_failures_data["all_runnables"]

        if self.granularity == "label":
            all_runnables = tuple(r for r in all_runnables if r.startswith("test-"))

        commit_tests = []
        for data in test_scheduling.generate_data(
            past_failures_data, commit_data, push_num, all_runnables, tuple(), tuple()
        ):
            commit_test = commit_data.copy()
            commit_test["test_job"] = data
            commit_tests.append(commit_test)

        probs = self.classify(commit_tests, probabilities=True)
        selected_indexes = np.argwhere(probs[:, 1] >= confidence)[:, 0]
        return {
            commit_tests[i]["test_job"]["name"]: math.floor(probs[i, 1] * 100) / 100
            for i in selected_indexes
        }

    def _get_cost(self, config: str) -> int:
        costs = [
            (("linux1804-64", "opt"), 2),
            (("linux1804-64", "debug"), 3),
            (("windows10", "opt"), 4),
            (("windows10", "debug"), 5),
            (("android-em", "opt"), 6),
            (("android-em", "debug"), 7),
            (("windows7", "opt"), 8),
            (("windows7", "debug"), 9),
            (("mac", "opt"), 10),
            (("mac", "debug"), 11),
            (("asan", "opt"), 12),
            (("asan", "debug"), 13),
            (("linux1804-32", "opt"), 14),
            (("linux1804-32", "debug"), 15),
            (("android-hw", "opt"), 16),
            (("android-hw", "debug"), 17),
            (("tsan", "opt"), 18),
            (("tsan", "debug"), 19),
            (("test-linux1804-64-shippable/opt-*-e10s",), 1),
        ]

        for substrings, cost in reversed(costs):
            if all(s in config for s in substrings):
                return cost

        raise Exception(f"Couldn't find cost for {config}")

    def _generate_equivalence_sets(
        self,
        tasks: Iterable[str],
        min_redundancy_confidence: float,
        load_failing_together: Callable[[str], Dict[str, Tuple[float, float]]],
        assume_redundant: bool,
    ) -> List[Set[str]]:
        # Generate 'equivalence sets', containing all tasks that are redundant with
        # each other.
        groups: List[Set[str]] = []
        task_to_groups: Dict[str, Set[int]] = collections.defaultdict(set)
        incompatible_groups: Dict[str, Set[int]] = collections.defaultdict(set)

        def create_group(task: str) -> None:
            if task in task_to_groups:
                return

            groups.append({task})
            task_to_groups[task] = {len(groups) - 1}

        # Add task1 to all equivalence groups where task2 is present, and likewise for task2.
        # Skip groups which contain tasks that are not redundant with task1.
        def add_to_groups(task1: str, task2: str) -> None:
            found = False

            if task1 in task_to_groups:
                for i in task_to_groups[task1]:
                    if task2 in incompatible_groups and i in incompatible_groups[task2]:
                        continue

                    groups[i].add(task2)
                    task_to_groups[task2].add(i)
                    found = True

            if task2 in task_to_groups:
                for i in task_to_groups[task2]:
                    if task1 in incompatible_groups and i in incompatible_groups[task1]:
                        continue

                    groups[i].add(task1)
                    task_to_groups[task1].add(i)
                    found = True

            # No suitable equivalence group was found for the tasks, create a new one.
            if found:
                return

            group = {task1, task2}
            groups.append(group)
            task_to_groups[task1].add(len(groups) - 1)
            task_to_groups[task2].add(len(groups) - 1)

        def mark_incompatible(task1: str, task2: str) -> None:
            if task1 in task_to_groups:
                incompatible_groups[task2].update(task_to_groups[task1])

            if task2 in task_to_groups:
                incompatible_groups[task1].update(task_to_groups[task2])

        sorted_tasks = sorted(tasks)
        for i, task1 in enumerate(sorted_tasks):
            try:
                failing_together_stats = load_failing_together(task1)
            except KeyError:
                if not assume_redundant:
                    create_group(task1)
                    continue
                else:
                    failing_together_stats = {}

            for task2 in sorted_tasks[i + 1 :]:
                try:
                    support, confidence = failing_together_stats[task2]
                except KeyError:
                    if not assume_redundant:
                        continue
                    else:
                        confidence = 1.0

                if confidence >= min_redundancy_confidence:
                    add_to_groups(task1, task2)
                else:
                    mark_incompatible(task1, task2)

            # Create group consisting only of task1, if there was nothing equivalent
            # with it.
            create_group(task1)

        return groups

    def _solve_optimization(self, solver: pywraplp.Solver) -> None:
        # The MIP solver is usually fast (milliseconds). If we hit a weird problem,
        # accept a suboptimal solution after 10 seconds.
        solver.SetTimeLimit(10000)
        status = solver.Solve()

        if status == pywraplp.Solver.INFEASIBLE:
            raise Exception("Infeasible problem")
        elif status == pywraplp.Solver.NOT_SOLVED:
            raise Exception("Problem unsolved")

    def reduce(
        self, tasks: Iterable[str], min_redundancy_confidence: float
    ) -> Set[str]:
        failing_together = test_scheduling.get_failing_together_db(self.granularity)

        def load_failing_together(task: str) -> Dict[str, Tuple[float, float]]:
            key = test_scheduling.failing_together_key(task)
            return pickle.loads(failing_together[key])

        solver = pywraplp.Solver(
            "select_configs", pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING
        )

        task_vars = {task: solver.BoolVar(task) for task in tasks}

        equivalence_sets = self._generate_equivalence_sets(
            tasks, min_redundancy_confidence, load_failing_together, False
        )

        # Create constraints to ensure at least one task from each set of equivalent
        # sets is selected.

        mutually_exclusive = True
        seen = set()
        for equivalence_set in equivalence_sets:
            if any(config in seen for config in equivalence_set):
                mutually_exclusive = False
                break

            seen |= equivalence_set

        for equivalence_set in equivalence_sets:
            sum_constraint = sum(task_vars[task] for task in equivalence_set)
            if mutually_exclusive:
                solver.Add(sum_constraint == 1)
            else:
                solver.Add(sum_constraint >= 1)

        # Choose the best set of tasks that satisfy the constraints with the lowest cost.
        solver.Minimize(
            sum(self._get_cost(task) * task_vars[task] for task in task_vars.keys())
        )

        self._solve_optimization(solver)

        return {
            task
            for task, task_var in task_vars.items()
            if task_var.solution_value() == 1
        }

    def select_configs(
        self, groups: Iterable[str], min_redundancy_confidence: float
    ) -> Dict[str, List[str]]:
        failing_together = test_scheduling.get_failing_together_db("config_group")

        all_configs = pickle.loads(failing_together[b"$ALL_CONFIGS$"])
        config_costs = {config: self._get_cost(config) for config in all_configs}

        solver = pywraplp.Solver(
            "select_configs", pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING
        )

        config_group_vars = {
            (config, group): solver.BoolVar(f"{group}@{config}")
            for group in groups
            for config in all_configs
        }

        for group in groups:
            key = test_scheduling.failing_together_key(group)
            try:
                failing_together_stats = pickle.loads(failing_together[key])
            except KeyError:
                failing_together_stats = {}

            def load_failing_together(config: str) -> Dict[str, Tuple[float, float]]:
                return failing_together_stats[config]

            equivalence_sets = self._generate_equivalence_sets(
                all_configs, min_redundancy_confidence, load_failing_together, True
            )

            # Create constraints to ensure at least one task from each set of equivalent
            # groups is selected.

            mutually_exclusive = True
            seen = set()
            for equivalence_set in equivalence_sets:
                if any(config in seen for config in equivalence_set):
                    mutually_exclusive = False
                    break

                seen |= equivalence_set

            for equivalence_set in equivalence_sets:
                sum_constraint = sum(
                    config_group_vars[(config, group)] for config in equivalence_set
                )
                if mutually_exclusive:
                    solver.Add(sum_constraint == 1)
                else:
                    solver.Add(sum_constraint >= 1)

        # Choose the best set of tasks that satisfy the constraints with the lowest cost.
        solver.Minimize(
            sum(
                config_costs[config] * config_group_vars[(config, group)]
                for config, group in config_group_vars.keys()
            )
        )

        self._solve_optimization(solver)

        configs_by_group: Dict[str, List[str]] = {}
        for group in groups:
            configs_by_group[group] = []

        for (config, group), config_group_var in config_group_vars.items():
            if config_group_var.solution_value() == 1:
                configs_by_group[group].append(config)

        return configs_by_group

    def evaluation(self) -> None:
        # Get a test set of pushes on which to test the model.
        pushes, train_push_len = self.get_pushes(False)

        # To evaluate the model with reductions enabled, we need to regenerate the failing together DB, using
        # only failure data from the training pushes (otherwise, we'd leak training information into the test
        # set).
        print("Generate failing together DB (restricted to training pushes)")
        push_data_iter, push_data_count, _ = test_scheduling.get_push_data(
            "label" if self.granularity == "label" else "config_group"
        )
        test_scheduling.generate_failing_together_probabilities(
            "label" if self.granularity == "label" else "config_group",
            push_data_iter(),
            push_data_count,
            pushes[train_push_len - 1]["revs"][0],
        )

        test_pushes_list = pushes[train_push_len:]

        all_tasks = reduce(
            lambda x, y: x | y,
            (
                set(push["failures"]) | set(push["passes"])
                for push in test_pushes_list[-28:]
            ),
        )

        test_pushes_failures = sum(
            1 for push in test_pushes_list if len(push["failures"]) > 0
        )

        test_pushes = {push["revs"][0]: push for push in test_pushes_list}

        print(
            f"Testing on {len(test_pushes)} ({test_pushes_failures} with failures) out of {len(pushes)}. {len(all_tasks)} schedulable tasks."
        )

        commit_map = get_commit_map()

        past_failures_data = test_scheduling.get_past_failures(self.granularity)
        last_push_num = past_failures_data["push_num"]
        past_failures_data.close()

        # Select tests for all the pushes in the test set.
        for i, (rev, push) in enumerate(tqdm(test_pushes.items())):
            commits = tuple(
                commit_map[revision]
                for revision in push["revs"]
                if revision in commit_map
            )
            if len(commits) == 0:
                test_pushes[rev]["all_possibly_selected"] = {}
                continue

            push_num = last_push_num - (len(test_pushes) - (i + 1))

            # Note: we subtract 100 to the push number to make sure we don't use
            # past failure data for the push itself.
            # The number 100 comes from the fact that in the past failure data
            # generation we store past failures in batches of 100 pushes.
            test_pushes[rev]["all_possibly_selected"] = self.select_tests(
                commits, 0.5, push_num - 100
            )

        reductions: List[Optional[float]] = [None, 0.9, 1.0]

        def do_eval(confidence_threshold, reduction, cap, minimum):
            for rev, push in test_pushes.items():
                selected = set(
                    name
                    for name, confidence in push["all_possibly_selected"].items()
                    if confidence >= confidence_threshold
                )

                if minimum is not None and len(selected) < minimum:
                    remaining = [
                        (name, confidence)
                        for name, confidence in push["all_possibly_selected"].items()
                        if name not in selected
                    ]
                    selected.update(
                        name
                        for name, _ in sorted(remaining, key=lambda x: -x[1])[
                            : minimum - len(selected)
                        ]
                    )

                if reduction is not None:
                    if self.granularity == "label":
                        selected = self.reduce(selected, reduction)
                    elif self.granularity == "group":
                        push["number_configs"] = len(
                            set(
                                config
                                for config, group in self.select_configs(
                                    selected, reduction
                                )
                            )
                        )

                if cap is not None and len(selected) > cap:
                    selected = set(
                        sorted(
                            (
                                (name, confidence)
                                for name, confidence in push[
                                    "all_possibly_selected"
                                ].items()
                                if name in selected
                            ),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:cap]
                    )

                caught = selected & set(push["failures"])

                push["number_scheduled"] = len(selected)
                push["caught_one"] = (
                    len(caught) > 0 if len(push["failures"]) != 0 else None
                )
                push["some_didnt_run"] = (
                    not selected.issubset(set(push["passes"]) | set(push["failures"])),
                )
                push["caught_percentage"] = (
                    len(caught) / len(push["failures"])
                    if len(push["failures"]) != 0
                    else None
                )

            min_scheduled = min(
                result["number_scheduled"] for result in test_pushes.values()
            )
            max_scheduled = max(
                result["number_scheduled"] for result in test_pushes.values()
            )
            average_scheduled = statistics.mean(
                result["number_scheduled"] for result in test_pushes.values()
            )
            num_failing_pushes = sum(
                1 for result in test_pushes.values() if result["caught_one"] is not None
            )
            num_caught_one = sum(
                1 for result in test_pushes.values() if result["caught_one"]
            )
            num_caught_one_or_some_didnt_run = sum(
                1
                for result in test_pushes.values()
                if result["caught_one"]
                or (result["caught_one"] is not None and result["some_didnt_run"])
            )
            percentage_caught_one = 100 * num_caught_one / num_failing_pushes
            percentage_caught_one_or_some_didnt_run = (
                100 * num_caught_one_or_some_didnt_run / num_failing_pushes
            )
            average_caught_percentage = 100 * statistics.mean(
                result["caught_percentage"]
                for result in test_pushes.values()
                if result["caught_percentage"] is not None
            )

            reduction_str = (
                f"enabled at {reduction * 100}%"
                if reduction is not None
                else "disabled"
            )

            message = f"For confidence threshold {confidence_threshold}, with reduction {reduction_str}, cap at {cap}, and minimum at {minimum}: scheduled {average_scheduled} tasks on average (min {min_scheduled}, max {max_scheduled}). In {percentage_caught_one}% of pushes we caught at least one failure ({percentage_caught_one_or_some_didnt_run}% ignoring misses when some of our selected tasks didn't run). On average, we caught {average_caught_percentage}% of all seen failures."

            if reduction is not None and self.granularity == "group":
                average_configs = statistics.mean(
                    result["number_configs"] for result in test_pushes.values()
                )
                message += f" On average, we selected {average_configs} configs."

            print(message)

        for minimum in [None, 10]:
            for cap in [None, 300, 500]:
                for reduction in reductions:
                    for confidence_threshold in [0.5, 0.7, 0.8, 0.85, 0.9, 0.95]:
                        do_eval(confidence_threshold, reduction, cap, minimum)

    def get_feature_names(self):
        return self.extraction_pipeline.named_steps["union"].get_feature_names()


class TestLabelSelectModel(TestSelectModel):
    def __init__(self, lemmatization=False):
        TestSelectModel.__init__(self, lemmatization, "label", failures_skip=60)


class TestGroupSelectModel(TestSelectModel):
    def __init__(self, lemmatization=False):
        TestSelectModel.__init__(self, lemmatization, "group")


class TestConfigGroupSelectModel(TestSelectModel):
    def __init__(self, lemmatization=False):
        TestSelectModel.__init__(self, lemmatization, "config_group")
