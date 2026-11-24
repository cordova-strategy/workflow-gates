import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from helpers import write_prewarmed_stub
from transcript_analysis import redaction, scope

from .conftest import (
    OTHER_REPOSITORY_CANARY_SKILL,
    _asst,
    _priced,
    _user_msg,
    _write_jsonl,
    _write_subagent_jsonl,
    init_repository_tracking,
    init_repository_tracking_canary_skill,
)


class TestProjectFamily:
    def test_raw_slug_with_worktree_suffix_collapses_to_base_slug(self):
        assert redaction._project_family("-home-u-repo-a--claude-worktrees-branch-x") == "-home-u-repo-a"

    def test_raw_slug_without_worktree_suffix_returns_unchanged(self):
        assert redaction._project_family("-home-u-repo-a") == "-home-u-repo-a"


class TestRootScopedDisplayLabel:
    """Direct unit coverage of redaction._root_scoped_display_label --
    cmd_subagents/cmd_subagent_mix exercise it only through their own
    redacted/disclosed output, so this class pins the disclosed path and its
    never-writes-into-redact_map invariant on their own."""

    @pytest.mark.parametrize("kind", ["branch", "agent-type"])
    def test_disclosed_label_is_account_prefixed_raw_value_and_leaves_map_empty(self, kind):
        redact_map: dict[tuple[int, str], str] = {}
        label = redaction._root_scoped_display_label(kind, 1, "feat-x", redact_map, disclose=True)
        assert label == "account-1/feat-x"
        assert redact_map == {}

    @pytest.mark.parametrize("kind", ["branch", "agent-type"])
    def test_non_disclosed_label_delegates_to_assign_root_scoped_redact_label(self, kind):
        redact_map: dict[tuple[int, str], str] = {}
        label = redaction._root_scoped_display_label(kind, 1, "feat-x", redact_map, disclose=False)
        assert label == redaction._assign_root_scoped_redact_label(kind, 1, "feat-x", {})
        assert redact_map == {(1, "feat-x"): label}

    def test_disclosed_call_interleaved_between_redacted_calls_does_not_shift_counter(self):
        """The direct proof of the "never writes into redact_map" invariant
        -- no integration test pins this unconditionally, since a real
        multi-root corpus can't isolate the counter position from the data
        it's built from."""
        redact_map: dict[tuple[int, str], str] = {}
        first = redaction._root_scoped_display_label("branch", 1, "a", redact_map, disclose=False)
        redaction._root_scoped_display_label("branch", 1, "disclosed-b", redact_map, disclose=True)
        second = redaction._root_scoped_display_label("branch", 1, "c", redact_map, disclose=False)
        assert first == "account-1/branch-1"
        assert second == "account-1/branch-2"

    def test_disclosed_and_redacted_labels_share_the_account_prefix_format(self):
        """Format-drift pin: a future change to either function's namespace
        string must fail here, substituting for extracting the format
        string into a third shared helper."""
        redact_map: dict[tuple[int, str], str] = {}
        disclosed = redaction._root_scoped_display_label("branch", 3, "feat-x", redact_map, disclose=True)
        redacted = redaction._assign_root_scoped_redact_label("branch", 3, "feat-y", {})
        assert disclosed.split("/", 1)[0] == redacted.split("/", 1)[0] == "account-3"

    def test_disclosed_label_strips_control_characters(self):
        """A gitBranch value is transcript-sourced, not git-validated -- an
        OSC-injection payload (the same fixture shape used for
        _format_cost_ledger_row's own control-character test) must not reach
        the disclosed label raw."""
        redact_map: dict[tuple[int, str], str] = {}
        label = redaction._root_scoped_display_label(
            "branch", 1, "\x1b]0;PWNED\x07\x1b[2J\x1b[H\x1b[31mFAKE-ROW\x1b[0m", redact_map, disclose=True
        )
        assert label == "account-1/]0;PWNED[2J[H[31mFAKE-ROW[0m"
        assert not re.search(r"[\x00-\x1f\x7f]", label)

    def test_disclosed_branch_value_containing_slash_stays_unambiguous(self):
        """Git branch names legitimately contain "/" (e.g. feature/foo) --
        the disclosed format itself uses "/" as the account-<K>/<value>
        separator, so this pins that a "/"-bearing value composes without
        truncation or reinterpretation."""
        redact_map: dict[tuple[int, str], str] = {}
        label = redaction._root_scoped_display_label("branch", 1, "feature/foo", redact_map, disclose=True)
        assert label == "account-1/feature/foo"
        assert label.split("/", 1) == ["account-1", "feature/foo"]


@pytest.mark.usefixtures("scrubbed_git_environment")
class TestRepoTrackedAgentTypeNames:
    """_repo_tracked_agent_type_names -- the --this-repo subagent_type
    disclosure allowlist accessor."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """lru_cache(maxsize=1) is process-global; cleared before and after
        every test in this class so a monkeypatched _REPO_AGENT_DEFINITIONS_DIR
        from one test can never leak a stale cached result into the next,
        including the real-directory regression test below."""
        redaction._repo_tracked_agent_type_names.cache_clear()
        yield
        redaction._repo_tracked_agent_type_names.cache_clear()

    def _init_agents_repo(self, tmp_path: Path, *, tracked: list[str], untracked: list[str] = ()) -> Path:
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=agents_dir, check=True)
        for name in tracked:
            (agents_dir / f"{name}.md").write_text("---\nname: x\n---\n")
        if tracked:
            subprocess.run(["git", "add", "--", *(f"{n}.md" for n in tracked)], cwd=agents_dir, check=True)
        for name in untracked:
            (agents_dir / f"{name}.md").write_text("---\nname: x\n---\n")
        return agents_dir

    def _patch_dir(self, monkeypatch, agents_dir: Path) -> None:
        monkeypatch.setattr(redaction, "_REPO_AGENT_DEFINITIONS_DIR", agents_dir)

    def test_tracked_md_stem_is_allowlisted(self, tmp_path, monkeypatch):
        agents_dir = self._init_agents_repo(tmp_path, tracked=["my-agent"])
        self._patch_dir(monkeypatch, agents_dir)
        assert "my-agent" in redaction._repo_tracked_agent_type_names()

    def test_untracked_md_file_in_same_directory_is_not_allowlisted(self, tmp_path, monkeypatch):
        agents_dir = self._init_agents_repo(tmp_path, tracked=["tracked-agent"], untracked=["scratch-agent"])
        self._patch_dir(monkeypatch, agents_dir)
        names = redaction._repo_tracked_agent_type_names()
        assert "tracked-agent" in names
        assert "scratch-agent" not in names

    def test_differently_cased_query_against_tracked_stem_is_excluded(self, tmp_path, monkeypatch):
        agents_dir = self._init_agents_repo(tmp_path, tracked=["code-writer"])
        self._patch_dir(monkeypatch, agents_dir)
        names = redaction._repo_tracked_agent_type_names()
        assert "code-writer" in names
        assert "Code-Writer" not in names

    def test_directory_outside_any_git_repo_yields_built_ins_alone(self, tmp_path, monkeypatch):
        agents_dir = tmp_path / "not-a-repo"
        agents_dir.mkdir()
        self._patch_dir(monkeypatch, agents_dir)
        assert redaction._repo_tracked_agent_type_names() == redaction._BUILT_IN_AGENT_TYPES

    def test_module_outside_the_checkout_layout_yields_built_ins_alone_without_running_git(self, monkeypatch):
        monkeypatch.setattr(redaction, "_REPO_AGENT_DEFINITIONS_DIR", None)

        def git_must_not_run(cmd, *a, **k):
            raise AssertionError("git ran for a module outside the checkout layout")
        monkeypatch.setattr(subprocess, "run", git_must_not_run)

        assert redaction._repo_tracked_agent_type_names() == redaction._BUILT_IN_AGENT_TYPES

    @pytest.mark.parametrize("agents_dir_kind", ["tracked", "untracked", "not_a_repo"])
    def test_built_ins_present_in_every_case(self, tmp_path, monkeypatch, agents_dir_kind):
        if agents_dir_kind == "not_a_repo":
            agents_dir = tmp_path / "not-a-repo"
            agents_dir.mkdir()
        elif agents_dir_kind == "tracked":
            agents_dir = self._init_agents_repo(tmp_path, tracked=["tracked-agent"])
        else:
            agents_dir = self._init_agents_repo(tmp_path, tracked=[], untracked=["scratch-agent"])
        self._patch_dir(monkeypatch, agents_dir)
        assert redaction._repo_tracked_agent_type_names().issuperset(redaction._BUILT_IN_AGENT_TYPES)

    def test_git_binary_missing_falls_back_to_built_ins_only(self, tmp_path, monkeypatch):
        """Matches TestRepoScopedProjectSlugsGuard's own FileNotFoundError
        precedent for _repo_scoped_project_slugs, diverging in outcome: this
        accessor deliberately fails closed to the built-ins frozenset rather
        than sys.exit, since failing closed here means more redaction, and
        an operator's report should not die because git is unavailable."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        self._patch_dir(monkeypatch, agents_dir)

        def boom(cmd, *a, **k):
            raise FileNotFoundError("git")
        monkeypatch.setattr(subprocess, "run", boom)
        assert redaction._repo_tracked_agent_type_names() == redaction._BUILT_IN_AGENT_TYPES

    def test_git_call_timeout_falls_back_to_built_ins_only(self, tmp_path, monkeypatch):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        self._patch_dir(monkeypatch, agents_dir)

        def boom(cmd, *a, **k):
            raise subprocess.TimeoutExpired(cmd, 10)
        monkeypatch.setattr(subprocess, "run", boom)
        assert redaction._repo_tracked_agent_type_names() == redaction._BUILT_IN_AGENT_TYPES

    def test_nested_tracked_agent_file_is_not_allowlisted(self, tmp_path, monkeypatch):
        """_repo_tracked_agent_type_names matches top-level entries only
        (no "/" in the path), matching _declared_pin's own flat
        agents_dir / f"{agent_type}.md" resolution -- a nested tracked file
        over-redacts, the safe direction."""
        agents_dir = self._init_agents_repo(tmp_path, tracked=["top-level-agent"])
        nested_dir = agents_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "nested-agent.md").write_text("---\nname: x\n---\n")
        subprocess.run(["git", "add", "--", "nested/nested-agent.md"], cwd=agents_dir, check=True)
        self._patch_dir(monkeypatch, agents_dir)
        names = redaction._repo_tracked_agent_type_names()
        assert "top-level-agent" in names
        assert "nested-agent" not in names

    def test_non_ascii_tracked_filename_is_allowlisted(self, tmp_path, monkeypatch):
        """Pins the docstring's -z rationale: without -z, git quotes and
        escapes unusual path names, corrupting the stem."""
        agents_dir = self._init_agents_repo(tmp_path, tracked=["café-agent"])
        self._patch_dir(monkeypatch, agents_dir)
        assert "café-agent" in redaction._repo_tracked_agent_type_names()

    def test_exported_git_dir_of_another_repository_never_yields_that_repositorys_agent_types(
        self, tmp_path, monkeypatch,
    ):
        (tmp_path / "own").mkdir()
        (tmp_path / "foreign").mkdir()
        own_dir = self._init_agents_repo(tmp_path / "own", tracked=["own-agent"])
        foreign_dir = self._init_agents_repo(tmp_path / "foreign", tracked=["foreign-agent"])
        self._patch_dir(monkeypatch, own_dir)
        monkeypatch.setenv("GIT_DIR", str(foreign_dir / ".git"))

        names = redaction._repo_tracked_agent_type_names()

        assert "own-agent" in names
        assert "foreign-agent" not in names

    def test_tracked_path_that_is_not_utf8_does_not_raise_and_the_other_names_stay_allowlisted(
        self, tmp_path, monkeypatch,
    ):
        fake_git = tmp_path / "bin" / "git"
        fake_git.parent.mkdir()
        write_prewarmed_stub(fake_git, "#!/bin/sh\nprintf 'caf\\351-agent.md\\0good-agent.md\\0'\n")
        monkeypatch.setenv("PATH", f"{fake_git.parent}:{os.environ['PATH']}")

        names = redaction._repo_tracked_agent_type_names()

        assert "good-agent" in names

    def test_real_agents_directory_allowlists_code_writer(self):
        """The ticket's own motivating scenario, against the real,
        unmonkeypatched agents/ directory -- deriving the name dynamically
        (next(dir.glob('*.md')).stem) would make both this test's intent
        and its failure message unreadable, so the name is hardcoded; the
        unit tests above already carry the "real derivation works" fact."""
        assert "code-writer" in redaction._repo_tracked_agent_type_names()

    def test_real_agents_directory_is_the_agents_directory_of_the_checkout_root(self):
        assert redaction._REPO_ROOT is not None
        assert redaction._REPO_AGENT_DEFINITIONS_DIR == redaction._REPO_ROOT / "claude" / ".claude" / "agents"
        assert redaction._REPO_AGENT_DEFINITIONS_DIR.is_dir()


class TestCheckoutRoot:
    def test_module_reached_through_a_symlinked_directory_yields_the_resolved_checkout_root(self, tmp_path):
        checkout = tmp_path / "checkout"
        module_directory = checkout / "claude" / ".claude" / "scripts" / "transcript_analysis"
        module_directory.mkdir(parents=True)
        (module_directory / "redaction.py").write_text("")
        stow_link = tmp_path / "stowed-config" / ".claude"
        stow_link.parent.mkdir()
        stow_link.symlink_to(checkout / "claude" / ".claude")

        root = redaction._checkout_root(stow_link / "scripts" / "transcript_analysis" / "redaction.py")

        assert root == checkout.resolve()

    def test_repo_root_is_the_directory_five_levels_above_the_module_file(self):
        module_path = Path(redaction.__file__).resolve()

        assert redaction._REPO_ROOT is not None
        assert redaction._REPO_ROOT / "claude" / ".claude" / "scripts" / "transcript_analysis" / module_path.name == module_path

    def test_module_path_in_the_checkout_layout_with_exactly_one_ancestor_above_it_yields_that_ancestor(self):
        module_file = Path("/claude/.claude/scripts/transcript_analysis/redaction.py")

        assert redaction._checkout_root(module_file) == Path("/")

    def test_module_path_in_the_checkout_layout_with_one_ancestor_too_few_yields_no_checkout_root(self):
        module_file = Path("/.claude/scripts/transcript_analysis/redaction.py")

        assert redaction._checkout_root(module_file) is None

    @pytest.mark.parametrize(
        "module_file",
        [
            "/zz-unused/vendored/lib/site/transcript_analysis/redaction.py",
            "/zz-unused/claude/.claude/scripts/lib/transcript_analysis/redaction.py",
            "/zz-unused/claude/.claude/scripts/transcript_analysis/nested/redaction.py",
            "/zz-unused/opt/.claude/scripts/transcript_analysis/redaction.py",
        ],
        ids=[
            "deep-layout-without-the-checkout-tail",
            "extra-directory-inside-the-tail",
            "module-below-the-package",
            "plain-copy-missing-the-claude-segment-of-the-tail",
        ],
    )
    def test_module_path_outside_the_checkout_layout_yields_no_checkout_root_however_many_ancestors_it_has(
        self, module_file,
    ):
        assert redaction._checkout_root(Path(module_file)) is None

    def test_copy_of_the_module_outside_the_checkout_layout_allowlists_the_built_in_agent_types_alone(self, tmp_path):
        copy_path = tmp_path / "lib" / "site" / "transcript_analysis" / "redaction.py"
        copy_path.parent.mkdir(parents=True)
        shutil.copyfile(redaction.__file__, copy_path)
        spec = importlib.util.spec_from_file_location("redaction_copy_outside_the_checkout_layout", copy_path)
        module_copy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module_copy)

        assert module_copy._REPO_ROOT is None
        assert module_copy._REPO_AGENT_DEFINITIONS_DIR is None
        assert module_copy._repo_tracked_agent_type_names() == redaction._BUILT_IN_AGENT_TYPES
        assert module_copy._repo_tracked_skill_names() == frozenset()


@pytest.mark.usefixtures("scrubbed_git_environment")
class TestRepoTrackedSkillNames:
    """_repo_tracked_skill_names -- the skill-reinjection name allowlist accessor."""

    @pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
    def test_every_local_variable_git_lists_less_the_config_variables_is_stripped(self):
        listed_by_git = subprocess.run(
            ["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True, check=True, timeout=10,
        ).stdout.split()

        locating_variables_git_lists = {name for name in listed_by_git if not name.startswith("GIT_CONFIG")}

        assert locating_variables_git_lists <= redaction._REPOSITORY_LOCATING_GIT_VARIABLES

    def test_no_git_config_variable_is_stripped(self):
        """`GIT_CONFIG_COUNT` and its siblings carry settings such as `safe.directory`, so stripping one makes
        `git -C <checkout>` refuse a checkout it does not trust."""
        assert not {name for name in redaction._REPOSITORY_LOCATING_GIT_VARIABLES if name.startswith("GIT_CONFIG")}

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """lru_cache(maxsize=1) is process-global; cleared before and after every test so a monkeypatched
        _REPO_ROOT never leaks a stale cached result into the next test."""
        redaction._repo_tracked_skill_names.cache_clear()
        yield
        redaction._repo_tracked_skill_names.cache_clear()

    def test_tracked_name_in_each_of_the_three_kept_shapes_is_in_and_an_untracked_file_in_the_same_tree_is_out(
        self, tmp_path, monkeypatch,
    ):
        repo_root = init_repository_tracking(
            tmp_path / "repo",
            tracked=[
                "claude-skills/skills/bare-skill/SKILL.md",
                ".claude/skills/project-skill/SKILL.md",
                "plugins/some-plugin/skills/plugin-skill/SKILL.md",
            ],
            untracked=["claude-skills/skills/scratch-skill/SKILL.md", "plugins/some-plugin/skills/scratch/SKILL.md"],
        )
        monkeypatch.setattr(redaction, "_REPO_ROOT", repo_root)

        assert redaction._repo_tracked_skill_names() == frozenset(
            {"bare-skill", "project-skill", "some-plugin:plugin-skill"}
        )

    @pytest.mark.parametrize(
        "nested_path",
        [
            "claude-skills/skills/skill/nested/SKILL.md",
            "plugins/some-plugin/skills/skill/nested/SKILL.md",
            ".claude/skills/skill/nested/SKILL.md",
            "claude-skills/skills/skill/REFERENCES.md",
            "claude-skills/other/skill/SKILL.md",
            "other/skills/skill/SKILL.md",
            "plugins/some-plugin/commands/skill/SKILL.md",
            "plugins/some-plugin/skills/skill/REFERENCES.md",
            "other-dir/some-plugin/skills/skill/SKILL.md",
            "SKILL.md",
        ],
    )
    def test_path_outside_the_three_kept_shapes_yields_no_name(self, tmp_path, monkeypatch, nested_path):
        monkeypatch.setattr(redaction, "_REPO_ROOT", init_repository_tracking(tmp_path / "repo", tracked=[nested_path]))

        assert redaction._repo_tracked_skill_names() == frozenset()

    def test_tracked_path_that_is_not_utf8_does_not_raise_and_the_other_skill_names_come_back(
        self, tmp_path, monkeypatch,
    ):
        fake_git = tmp_path / "bin" / "git"
        fake_git.parent.mkdir()
        write_prewarmed_stub(
            fake_git,
            "#!/bin/sh\n"
            "printf 'claude-skills/skills/caf\\351-skill/SKILL.md\\0claude-skills/skills/good-skill/SKILL.md\\0'\n",
        )
        monkeypatch.setenv("PATH", f"{fake_git.parent}:{os.environ['PATH']}")

        names = redaction._repo_tracked_skill_names()

        assert "good-skill" in names

    def test_tracked_non_ascii_skill_name_comes_back_whole(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            redaction, "_REPO_ROOT",
            init_repository_tracking(tmp_path / "repo", tracked=["claude-skills/skills/caf\u00e9-skill/SKILL.md"]),
        )

        assert redaction._repo_tracked_skill_names() == frozenset({"caf\u00e9-skill"})

    def test_module_with_no_checkout_root_yields_the_empty_set_without_running_git(self, monkeypatch):
        def fail_if_git_runs(command, *args, **kwargs):
            raise AssertionError("git ran with no checkout root")

        monkeypatch.setattr(redaction, "_REPO_ROOT", None)
        monkeypatch.setattr(subprocess, "run", fail_if_git_runs)

        assert redaction._repo_tracked_skill_names() == frozenset()

    def test_directory_outside_any_git_repo_yields_the_empty_set(self, tmp_path, monkeypatch):
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        monkeypatch.setattr(redaction, "_REPO_ROOT", not_a_repo)

        assert redaction._repo_tracked_skill_names() == frozenset()

    @pytest.mark.parametrize(
        "failure", [FileNotFoundError("git"), subprocess.TimeoutExpired("git", 10)], ids=["git-missing", "git-timeout"],
    )
    def test_git_failure_yields_the_empty_set(self, tmp_path, monkeypatch, failure):
        def raise_failure(cmd, *args, **kwargs):
            raise failure

        monkeypatch.setattr(subprocess, "run", raise_failure)

        assert redaction._repo_tracked_skill_names() == frozenset()

    def test_working_directory_inside_a_second_repository_never_yields_that_repositorys_names(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.chdir(init_repository_tracking_canary_skill(tmp_path / "other"))

        names = redaction._repo_tracked_skill_names()

        assert names, "git could not list this checkout's tracked files (ownership, or a checkout without .git)"
        assert OTHER_REPOSITORY_CANARY_SKILL not in names
        assert "code-review" in names

    @pytest.mark.parametrize(
        ("variable", "foreign_git_path"), [("GIT_DIR", ".git"), ("GIT_INDEX_FILE", ".git/index")],
    )
    def test_exported_git_variable_of_another_repository_never_yields_that_repositorys_names(
        self, tmp_path, monkeypatch, variable, foreign_git_path,
    ):
        own_root = init_repository_tracking(tmp_path / "own", tracked=[".claude/skills/own-skill/SKILL.md"])
        foreign_root = init_repository_tracking(tmp_path / "foreign", tracked=[".claude/skills/foreign-skill/SKILL.md"])
        monkeypatch.setattr(redaction, "_REPO_ROOT", own_root)
        monkeypatch.setenv(variable, str(foreign_root / foreign_git_path))

        assert redaction._repo_tracked_skill_names() == frozenset({"own-skill"})


class TestCorpusFingerprintRootRemovalLimits:
    """_corpus_fingerprint hashes the raw-label SET, not root count --
    removing a root whose labels are a strict subset of a surviving root's
    own labels is invisible to the fingerprint, by design, not by bug."""

    def test_fingerprint_unchanged_when_removed_roots_labels_are_a_subset_of_a_surviving_root(self):
        two_root_map = {
            (0, "shared-label"): "account-1/private-project-1",
            (1, "shared-label"): "account-2/private-project-1",
        }
        one_root_map = {"shared-label": "private-project-1"}
        # Root 2's only label ("shared-label") is a strict subset of root 1's
        # own label set, so dropping root 2 does not change the label SET —
        # the fingerprint is identical even though the account count changed.
        assert redaction._corpus_fingerprint(two_root_map) == redaction._corpus_fingerprint(one_root_map)


class TestBuildRedactMapDirectUnit:
    """Direct unit coverage of _build_redact_map's multi-root ordinal-
    assignment math — the many end-to-end subcommand tests exercise this
    function only through a full report run; this pins its returned dict's
    keys/values directly when the same raw project label collides across two
    declared roots."""

    def test_two_roots_with_colliding_raw_label_map_to_distinct_account_scoped_keys(self, tmp_path):
        root_a = tmp_path / "acct-a" / "projects"
        proj_a = root_a / "-home-user-testrepo"
        proj_a.mkdir(parents=True)
        _write_jsonl(proj_a / "sess-a.jsonl", [_asst("claude-sonnet-4-6", branch="from-a")])

        root_b = tmp_path / "acct-b" / "projects"
        proj_b = root_b / "-home-user-testrepo"
        proj_b.mkdir(parents=True)
        _write_jsonl(proj_b / "sess-b.jsonl", [_asst("claude-sonnet-4-6", branch="from-b")])

        ordinals = scope._redaction_ordinals([root_a, root_b])
        ordinal_a, ordinal_b = ordinals[root_a.resolve()], ordinals[root_b.resolve()]

        redact_map = redaction._build_redact_map([root_a, root_b])

        assert redact_map == {
            (ordinal_a, "testrepo"): f"account-{ordinal_a}/private-project-1",
            (ordinal_b, "testrepo"): f"account-{ordinal_b}/private-project-1",
        }

    def test_subagent_only_project_with_unpriced_turns_still_shifts_sibling_ordinal(self, tmp_path):
        """A project whose main .jsonl is empty and whose only subagent turn
        carries no priced usage is still included in the label census
        (iter_sessions only requires a non-empty records list, not priced
        usage) — shifting a sorted-later priced sibling's ordinal even
        though the phantom project itself is never looked up
        (_cost_report's `if session_total:` gate skips zero-total
        sessions)."""
        root = tmp_path / "acct-a"
        phantom = root / "-home-user-aaa-phantom"
        phantom.mkdir(parents=True)
        _write_jsonl(phantom / "sess-phantom.jsonl", [])
        _write_subagent_jsonl(phantom, "sess-phantom", "agent-1", [_user_msg("hi")])

        priced = root / "-home-user-zzz-priced"
        priced.mkdir(parents=True)
        _write_jsonl(priced / "sess-priced.jsonl", [_priced("claude-sonnet-5", input=1_000_000)])

        redact_map = redaction._build_redact_map([root])
        assert redact_map["zzz-priced"] == "private-project-2"

    def test_two_subagent_only_projects_get_distinct_sorted_labels(self, tmp_path):
        """Sibling of the single-phantom ordinal-shift case above: two
        projects visible only through subagent transcripts still get
        distinct labels in sorted order, not a collision or a shared slot."""
        root = tmp_path / "acct-a"
        proj_a = root / "-home-user-aaa-phantom"
        proj_a.mkdir(parents=True)
        _write_jsonl(proj_a / "sess-a.jsonl", [])
        _write_subagent_jsonl(proj_a, "sess-a", "agent-1", [_user_msg("hi")])

        proj_b = root / "-home-user-zzz-phantom"
        proj_b.mkdir(parents=True)
        _write_jsonl(proj_b / "sess-b.jsonl", [])
        _write_subagent_jsonl(proj_b, "sess-b", "agent-1", [_user_msg("hi")])

        redact_map = redaction._build_redact_map([root])
        assert redact_map == {
            "aaa-phantom": "private-project-1",
            "zzz-phantom": "private-project-2",
        }


class TestUntrackedAgentTypeLabels:
    """_untracked_agent_type_labels -- the `reviewer-yield --redact` label map."""

    def test_tracked_name_maps_to_itself(self, stub_repo_tracked_agent_types):
        stub_repo_tracked_agent_types("tracked-agent")
        assert redaction._untracked_agent_type_labels(["tracked-agent"]) == {"tracked-agent": "tracked-agent"}

    def test_built_in_name_maps_to_itself(self, stub_repo_tracked_agent_types):
        stub_repo_tracked_agent_types()
        assert redaction._untracked_agent_type_labels(["general-purpose"]) == {"general-purpose": "general-purpose"}

    def test_untracked_names_are_numbered_in_sorted_order_regardless_of_input_order(
        self, stub_repo_tracked_agent_types,
    ):
        stub_repo_tracked_agent_types()
        labels = redaction._untracked_agent_type_labels(["zeta-agent", "alpha-agent"])
        assert labels == {"alpha-agent": "agent-type-1", "zeta-agent": "agent-type-2"}

    def test_a_tracked_name_does_not_consume_a_number(self, stub_repo_tracked_agent_types):
        stub_repo_tracked_agent_types("tracked-agent")
        labels = redaction._untracked_agent_type_labels(["alpha-agent", "tracked-agent", "zeta-agent"])
        assert labels == {"alpha-agent": "agent-type-1", "tracked-agent": "tracked-agent", "zeta-agent": "agent-type-2"}

    def test_a_repeated_name_gets_one_label(self, stub_repo_tracked_agent_types):
        stub_repo_tracked_agent_types()
        labels = redaction._untracked_agent_type_labels(["alpha-agent", "alpha-agent"])
        assert labels == {"alpha-agent": "agent-type-1"}

    def test_no_names_yields_an_empty_map(self, stub_repo_tracked_agent_types):
        stub_repo_tracked_agent_types()
        assert redaction._untracked_agent_type_labels([]) == {}
