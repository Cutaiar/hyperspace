"""The conflict sheet's replace machinery, generic.

No kind is replaceable: the dream is an effect, any number of instances, and
`patches.REPLACEABLE` is empty. What is checked is the machinery's own: every
single-instance node is refused in words, the replaced values read by what a
node owns for any kind, and a landing held across a hot reload.
"""

from __future__ import annotations

from test_patches import parts
from test_patches_frame_kinds import on_graph, rig, wake_doc  # noqa: F401
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import patches, ui_graph
from hyperspace.patches import Host, spawn


def test_no_kind_is_replaceable_and_the_dream_is_not_one_per_frame():
    assert patches.REPLACEABLE == ()
    assert "dream" not in patches.ONE_PER_FRAME


def test_the_single_instance_kinds_are_refused_and_name_only_themselves():
    p = parts(wake_doc())
    whole, _ = patches.lift(*p, ["render:scene", "render:shape"])
    landing = spawn({**whole, "name": "x"}, Host.of(*p[:2]))
    assert landing.replacing == ()
    assert landing.refusal == patches.TAKEN_WORDS.format(name="x", nodes="scene, shape")


def test_the_replaced_values_read_what_the_node_owns_for_any_kind(rig):  # noqa: F811
    """The door for the other kinds: a shape's fresh values are by what it
    owns (`rot.*`, most of `view.*`), not a group of its name."""
    on_graph(rig, "party-wake")
    e = ui_graph.group_edit(rig.panel)
    got = e._replaced_values({}, ("shape",))
    assert "view.bright" in got and "view.pattern" not in got
    assert any(k.startswith("rot.") for k in got) or not any(
        p.id.startswith("rot.") and p.persist for p in rig.reg)
    assert all(patches.node_members(("shape",)).owns(k) for k in got)


def test_a_landing_from_before_a_hot_reload_still_refuses_or_lands(rig):  # noqa: F811
    """A sheet held across a reload holds the old class: no `replacing`, no
    `unanswered`, no AttributeError."""
    from types import SimpleNamespace
    on_graph(rig, "party-noita")
    e = ui_graph.group_edit(rig.panel)
    old = SimpleNamespace(group={"nodes": []}, modifiers=(), lfos=(), envs=())
    assert e._spawn_refusal(old) is None and e.replace_said(old) == ([], [])
