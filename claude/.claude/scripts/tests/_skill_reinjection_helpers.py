"""Builders and stubs test_transcript_skill_reinjection.py uses: compaction records and the tracked-skill allowlist
stub."""
from transcript_analysis import redaction, skill_reinjection

from ._compaction_context_helpers import compact_boundary, invoked_skills_attachment
from ._compaction_context_helpers import sidechain as mark_sidechain

# A name this repo tracks as a bare directory name, and one it tracks as a plugin skill.
TRACKED_SKILL = "sentinel-tracked-skill"
TRACKED_PLUGIN_SKILL = "sentinel-plugin:sentinel-plugin-skill"
UNTRACKED_SKILL = "sentinel-untracked-skill"

# Values that must never reach stdout or stderr.
SESSION_ID_CANARY = "canary-session-id"
DIRECTORY_CANARY = "/srv/canary-project"
PATH_CANARY = f"{DIRECTORY_CANARY}/skills/canary/SKILL.md"
CONTENT_CANARY = f"Base directory for this skill: {DIRECTORY_CANARY}/skills/canary"

CUT_LENGTH = 20_000

UNSET = object()


def boundary(uuid: object = "boundary-1", timestamp: object = "2026-01-02T03:04:05.000Z", *, sidechain: bool = False) -> dict:
    """A `compact_boundary` record in the recorded shape, with a `timestamp` and a `uuid`. `uuid=UNSET` leaves the key out."""
    record: dict = {**compact_boundary(), "timestamp": timestamp}
    if uuid is not UNSET:
        record["uuid"] = uuid
    return mark_sidechain(record) if sidechain else record


def skill_entry(name: str, content: str = "1. First step.", path: str = PATH_CANARY) -> dict:
    return {"name": name, "path": path, "content": content}


def attachment(*skills: object, sidechain: bool = False) -> dict:
    """An `invoked_skills` attachment record holding `skills`."""
    record = invoked_skills_attachment(list(skills))
    return mark_sidechain(record) if sidechain else record


def cut_content(total_code_points: int = CUT_LENGTH) -> str:
    """A body of exactly `total_code_points` characters that ends in the truncation marker."""
    filler = total_code_points - len(skill_reinjection.TRUNCATION_MARKER) - 1
    return "x" * filler + "\n" + skill_reinjection.TRUNCATION_MARKER


def stub_tracked_skill_names(monkeypatch, *names: str) -> None:
    """Makes redaction treat exactly `names` as this repo's tracked skills, so a test needs no git repo."""
    tracked = frozenset(names)
    monkeypatch.setattr(redaction, "_repo_tracked_skill_names", lambda: tracked)
