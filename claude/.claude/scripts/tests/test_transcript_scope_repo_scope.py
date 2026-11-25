"""scope.py's --projects keywords on _add_project_scope_args and the _branch_never_joins_a_pr predicate."""
import argparse

import pytest
from transcript_analysis import scope

from .conftest import _option_help


class TestAddProjectScopeArgsProjectsKeywords:
    def test_a_caller_that_omits_both_keywords_keeps_the_machine_wide_default_and_no_projects_help(self):
        parser = argparse.ArgumentParser()
        scope._add_project_scope_args(parser)
        assert parser.get_default("projects") == "*"
        assert _option_help(parser, "--projects") is None

    def test_repo_scope_default_leaves_projects_unset_so_a_bare_run_differs_from_an_explicit_glob(self):
        parser = argparse.ArgumentParser()
        scope._add_project_scope_args(parser, repo_scope_default=True)
        assert parser.parse_args([]).projects is None
        assert parser.parse_args(["--projects", "*"]).projects == "*"

    def test_projects_help_keyword_sets_the_projects_help(self):
        parser = argparse.ArgumentParser()
        scope._add_project_scope_args(parser, projects_help="Select a caller-specific glob.")
        assert _option_help(parser, "--projects") == "Select a caller-specific glob."


class TestBranchNeverJoinsAPr:
    @pytest.mark.parametrize("branch", ["main", "master", "develop", "HEAD", "worktree-agent-x"])
    def test_default_branch_candidate_detached_head_and_worktree_agent_never_join(self, branch):
        assert scope._branch_never_joins_a_pr(branch) is True

    def test_an_ordinary_feature_branch_may_join(self):
        assert scope._branch_never_joins_a_pr("GH-1426/pr-cost-capture-scope") is False

    @pytest.mark.parametrize(
        "branch",
        [
            "maintenance",  # contains the candidate "main" without equaling it
            "HEAD-fix",  # starts with the detached-HEAD name without equaling it
            "worktree-agent",  # the agent prefix lacks its trailing hyphen
            "my-worktree-agent-x",  # the prefix text starts mid-word, not at the name's start
        ],
    )
    def test_a_name_that_only_resembles_a_never_join_name_may_join(self, branch):
        assert scope._branch_never_joins_a_pr(branch) is False
