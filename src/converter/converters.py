from __future__ import annotations
import uuid
from typing import Mapping, Union, List
from src.dto.state_dto import (
    RootRepoState, SelfBuiltComponent, Owner, Individual,
    RepoType, ComponentType,
)

def coerce_state(resp: Union[RootRepoState, Mapping[str, object]]) -> RootRepoState:
    # Already typed
    if isinstance(resp, RootRepoState):
        return resp

    # Unwrap common wrappers: {"output": {...}} or {"state": {...}}
    d = dict(resp)
    if isinstance(d.get("output"), dict):
        d = d["output"]
    if isinstance(d.get("state"), dict):
        d = d["state"]

    root = str(d.get("repo_root_url") or d.get("root_repo_url") or "")

    state = RootRepoState(repo_root_url=root)

    # Add deployable field handling
    deployable = d.get("deployable")
    if isinstance(deployable, bool):
        state.deployable = deployable
    elif isinstance(deployable, str):
        state.deployable = deployable.lower() == "true"
    else:
        state.deployable = False

    # repo_type can be Enum or str
    rt = d.get("repo_type")
    if isinstance(rt, RepoType):
        state.repo_type = rt
    elif isinstance(rt, str) and rt:
        try:
            state.repo_type = RepoType(rt)
        except ValueError:
            state.repo_type = None
    else:
        state.repo_type = None

    comps: List[SelfBuiltComponent] = []
    for c in (d.get("self_built_software") or []):
        if isinstance(c, SelfBuiltComponent):
            # normalize minimal fields
            if not c.display_url:
                c.display_url = root
            comps.append(c)
            continue
        if isinstance(c, str):
            # ← NEW: promote a bare name into a full component
            comps.append(
                SelfBuiltComponent(
                    name=c,
                    path="",
                    display_url=root,
                    owner=Owner(),
                    language=None,
                    component_type=ComponentType.UNKNOWN,
                )
            )
            continue
        if not isinstance(c, dict):
            continue

        owner_raw = c.get("owner") or {}
        owner = Owner(
            team=owner_raw.get("team"),
            individuals=[Individual(**i) for i in (owner_raw.get("individuals") or [])],
        )

        ct = c.get("component_type")
        if isinstance(ct, ComponentType):
            ctype = ct
        elif isinstance(ct, str):
            try:
                ctype = ComponentType(ct)
            except ValueError:
                ctype = ComponentType.UNKNOWN
        else:
            ctype = ComponentType.UNKNOWN

        comps.append(
            SelfBuiltComponent(
                id=c.get("id") or str(uuid.uuid4()),
                name=str(c.get("name") or ""),
                path=str(c.get("path") or ""),
                display_url=str(c.get("display_url") or root),
                owner=owner,
                language=c.get("language"),
                component_type=ctype,
            )
        )

    state.self_built_software = comps
    return state
