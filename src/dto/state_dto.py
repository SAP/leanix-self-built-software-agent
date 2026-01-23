from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.dto.context_dto import DiscoveryContext


class RepoType(str, Enum):
    MONO_REPO = "mono-repo"
    SINGLE_PURPOSE_REPO = "single-purpose-repo"


class ComponentType(str, Enum):
    FE = "FE"
    BE = "BE"
    LIBRARY = "library"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Individual:
    name: str
    github: Optional[str] = None
    emails: Optional[List[str]] = None


@dataclass(slots=True)
class Owner:
    team: Optional[str] = None
    individuals: List[Individual] = field(default_factory=list)

@dataclass(slots=True)
class Evidence:
    path: str
    snippet: str
    reason: str
@dataclass(slots=True)
class TechStack:
    name: str
    version: str
    confidence: str
    evidence: List[Evidence] = field(default_factory=list)


@dataclass(slots=True)
class SelfBuiltComponent:
    name: str
    path: str
    display_url: str
    owner: Owner
    evidence: str
    confidence: str
    tech_stacks: List[TechStack] = field(default_factory=list)
    language: Optional[List[dict]] = None
    component_type: ComponentType = ComponentType.UNKNOWN
    display_url: str


@dataclass(slots=True)
class RootRepoState:
    repo_root_url: str
    deployable: bool = False
    deployable_signal_files: List[str] = field(default_factory=list)
    local_path: Optional[str] = None
    repo_type: Optional[RepoType] = None
    self_built_software: List[SelfBuiltComponent] = field(default_factory=list)
    repo_type_evidence: Optional[str] = None
    discovery_context: Optional[DiscoveryContext] = None
    org_context_override: Optional[str] = None
    repo_context_override: Optional[str] = None


# A mapping from root_repo_url -> RootRepo
SelfBuiltByRepo = Dict[str, RootRepoState]


# ---------- Serialization helpers ----------

def _component_from_dict(d: Dict[str, Any]) -> SelfBuiltComponent:
    owner_raw = d.get("owner") or {}
    individuals_raw = owner_raw.get("individuals") or []
    owner = Owner(
        team=owner_raw.get("team"),
        individuals=[Individual(**i) for i in individuals_raw],
    )
    ctype = d.get("component_type") or "unknown"
    # tolerate strings in source JSON; coerce to enum
    try:
        ctype_enum = ComponentType(ctype)
    except ValueError:
        ctype_enum = ComponentType.UNKNOWN

    return SelfBuiltComponent(
        id=d["id"],
        name=d["name"],
        path=d.get("path", "") or "",
        display_url=d["display_url"],
        owner=owner,
        language=d.get("language"),
        component_type=ctype_enum,
        evidence=d.get("evidence", ""),
        confidence=d.get("confidence", ""),
    )


def _component_to_dict(c: SelfBuiltComponent) -> Dict[str, Any]:
    out = asdict(c)
    # Enums become their string values
    out["component_type"] = c.component_type.value
    return out


def _rootrepo_from_dict(d: Dict[str, Any]) -> RootRepoState:
    rkind = d.get("repo_kind") or RepoType.SINGLE_PURPOSE_REPO.value
    try:
        rkind_enum = RepoType(rkind)
    except ValueError:
        rkind_enum = RepoType.SINGLE_PURPOSE_REPO

    items = d.get("self_built_software") or []
    return RootRepoState(
        repo_type=rkind_enum,
        self_built_software=[_component_from_dict(x) for x in items],
    )


def _rootrepo_to_dict(r: RootRepoState) -> Dict[str, Any]:
    return {
        "repo_kind": r.repo_type.value,
        "self_built_software": [_component_to_dict(c) for c in r.self_built_software],
    }


def load_self_built_by_repo(path: str | Path) -> SelfBuiltByRepo:
    import json
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object mapping root_repo_url -> {...}")
    return {root: _rootrepo_from_dict(obj) for root, obj in data.items()}


def dump_self_built_by_repo(mapping: SelfBuiltByRepo, path: str | Path) -> None:
    import json
    serializable = {root: _rootrepo_to_dict(obj) for root, obj in mapping.items()}
    Path(path).write_text(json.dumps(serializable, indent=2), encoding="utf-8")
