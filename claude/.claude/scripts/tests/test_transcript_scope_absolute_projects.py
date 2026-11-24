"""_resolve_project_scope's handling of an absolute --projects value, with the relative-glob controls."""
import argparse

import pytest
from transcript_analysis import scope

from .conftest import _asst, _write_jsonl


class TestAbsoluteProjectsValue:
    """An absolute --projects value exits 2 before any scan, at every root count, while a relative glob
    keeps reading."""

    @pytest.mark.parametrize("projects_value", ["/abs/*", "//abs"])
    @pytest.mark.parametrize("root_count", [1, 2])
    def test_absolute_projects_value_exits_2_at_every_root_count(
        self, tmp_path, capsys, root_count, projects_value,
    ):
        """Path.glob raises NotImplementedError on an absolute pattern, so the single-root scan would die with
        a traceback after the caller had already started work."""
        roots = [tmp_path / f"acct-{index}" for index in range(root_count)]
        for root in roots:
            root.mkdir()
        args = argparse.Namespace(this_repo=False, projects=projects_value)

        with pytest.raises(SystemExit) as exc:
            scope._resolve_project_scope(args, "buckets", roots=roots)

        assert exc.value.code == 2
        captured = capsys.readouterr()
        assert "buckets: --projects:" in captured.err
        assert "not an absolute path" in captured.err
        assert captured.out == ""

    def test_absolute_projects_refusal_is_identical_whether_or_not_the_path_exists(self, tmp_path, capsys):
        """The refusal text is the same for an existing and a missing path, and it does not echo the supplied value."""
        existing_dir = tmp_path / "present-dir"
        existing_dir.mkdir()
        missing_dir = tmp_path / "absent-dir"
        root = tmp_path / "acct-a"
        root.mkdir()
        refusal_stderr = {}
        for label, supplied_dir in (("existing", existing_dir), ("missing", missing_dir)):
            args = argparse.Namespace(this_repo=False, projects=f"{supplied_dir}/*")

            with pytest.raises(SystemExit):
                scope._resolve_project_scope(args, "buckets", roots=[root])

            refusal_stderr[label] = capsys.readouterr().err
            assert str(supplied_dir) not in refusal_stderr[label]

        refusal = refusal_stderr["existing"]
        assert refusal.startswith("buckets: --projects:")
        assert "not an absolute path" in refusal
        assert "--this-repo" in refusal
        assert "--projects=" in refusal  # a name starting with '-' must be passed in the '=' form
        assert refusal_stderr["missing"] == refusal

    def test_double_star_projects_value_over_one_root_reads_every_depth_where_a_star_reads_one(self, tmp_path):
        """'**' is a relative glob, so the single-root scan accepts it and Path.glob recurses, where '*' stops at the
        project-directory level."""
        root = tmp_path / "acct-a"
        project_dir = root / "-repo-main"
        (project_dir / "sub").mkdir(parents=True)
        _write_jsonl(project_dir / "sess.jsonl", [_asst("claude-sonnet-4-6", branch="from-one-level")])
        _write_jsonl(project_dir / "sub" / "deep.jsonl", [_asst("claude-sonnet-4-6", branch="from-two-levels")])

        def branches_read(projects_value: str) -> set[str]:
            args = argparse.Namespace(this_repo=False, projects=projects_value)
            session_iter, _scope_label = scope._resolve_project_scope(args, "buckets", roots=[root])
            return {rec["gitBranch"] for _jsonl, records in session_iter for rec in records}

        assert branches_read("*") == {"from-one-level"}  # control: '*' does not reach the deeper session
        assert branches_read("**") == {"from-one-level", "from-two-levels"}

    def test_relative_projects_value_over_one_root_still_returns_its_generator(self, tmp_path):
        """Positive control for the absolute-value refusal: the same call with a relative glob does not exit."""
        root = tmp_path / "acct-a"
        root.mkdir()
        args = argparse.Namespace(this_repo=False, projects="*")

        session_iter, scope_label = scope._resolve_project_scope(args, "buckets", roots=[root])

        assert list(session_iter) == []
        assert scope_label == "*"
