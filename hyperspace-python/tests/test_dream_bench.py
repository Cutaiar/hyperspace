"""tools/dream_bench/g_layers.py: the layer × resolution × mode bench.

Its counting (multiply-adds per pixel, convs) is what the "Dreaming at
540p" cost model was built on, so it is checked against those figures; the
BN fold must not change what GoogLeNet computes; and a tiny run on the CPU
goes end to end (eager and fold only — a compiled mode needs a compiler
toolchain the runner may not have, and is the Mac's to measure).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torchvision")

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "tools" / "dream_bench"


@pytest.fixture(scope="module")
def g():
    sys.path.insert(0, str(BENCH))       # the bench's own `common`
    try:
        spec = importlib.util.spec_from_file_location("g_layers", BENCH / "g_layers.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["g_layers"] = mod        # its dataclasses look their module up
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop("g_layers", None)
        sys.path.remove(str(BENCH))


def test_modes_read_as_one_backend_and_its_flags(g):
    assert g.parse_mode("eager") == g.Mode("eager")
    assert g.parse_mode("fold+inductor") == g.Mode("inductor", fold=True)
    assert g.parse_mode("cl+fold+step") == g.Mode("step", fold=True, cl=True)
    assert g.parse_mode("fold").name == "fold"
    assert g.parse_mode("fold+cl+max").name == "fold+cl+max"
    with pytest.raises(ValueError, match="one backend"):
        g.parse_mode("aot+inductor")
    with pytest.raises(ValueError, match="unknown"):
        g.parse_mode("fast")


def test_layer_names_and_groups(g):
    from hyperspace import dream

    assert g.pick_layers("all") == list(dream.TRUNKS)
    assert g.pick_layers("conv3_3,vgg")[0] == "conv3_3"          # no repeats, order kept
    assert len(g.pick_layers("conv3_3,vgg")) == 13
    assert all(dream.TRUNKS[n][0] == "googlenet" for n in g.pick_layers("googlenet"))
    assert set(g.SHALLOW) <= set(dream.TRUNKS)
    with pytest.raises(ValueError, match="unknown layer"):
        g.pick_layers("conv9_9")


@pytest.mark.parametrize(("layer", "size", "convs", "macs_px"), [
    ("conv1_1", (64, 48), 1, 1728),
    ("conv3_3", (64, 48), 7, 186048),
    ("conv5_3", (64, 48), 13, 305856),
    ("conv1", (224, 224), 1, 2352),           # GoogLeNet's stem, the paper's 118 M at 224²
])
def test_the_counts_are_the_cost_models(g, layer, size, convs, macs_px):
    from hyperspace import dream

    arch, cut = dream.TRUNKS[layer]
    stacks = g.Stacks(torch.device("cpu"), None)
    net = dream.cut_stack(arch, stacks.get(arch, torch.float32, g.Mode("eager")), cut)
    w, h = size
    got = g.conv_cost(net, torch.rand((1, 3, h, w)))
    assert got[0] == convs
    assert got[1] == pytest.approx(macs_px)


def test_googlenet_has_57_convs_to_inception5b_and_folding_keeps_its_output(g):
    from hyperspace import dream

    torch.manual_seed(0)
    stack = dream.net_stack("googlenet", None)
    for _, m in stack:
        m.eval()
        for mod in m.modules():                # random BN statistics, so the fold has work
            if isinstance(mod, torch.nn.BatchNorm2d):
                mod.running_mean.uniform_(-0.5, 0.5)
                mod.running_var.uniform_(0.5, 2.0)
    net = dream.cut_stack("googlenet", stack, "inception5b")
    x = torch.rand((1, 3, 96, 160))
    with torch.no_grad():
        before = net(x)
    assert g.fold_bn(stack) == 57
    with torch.no_grad():
        after = dream.cut_stack("googlenet", stack, "inception5b")(x)
    assert torch.allclose(before, after, atol=1e-4, rtol=1e-3)
    assert not any(isinstance(m, torch.nn.BatchNorm2d) for m in net.modules())


def test_the_fit_recovers_its_four_terms(g):
    fixed, o, p, c = 1.5, 0.04, 5.3, 0.63       # GoogLeNet folded, M3 Max, 2026-11-25
    rows = []
    for convs, macs in ((1, 2352), (3, 9519), (9, 12070), (33, 23331)):
        for w, h in ((456, 256), (960, 540), (1920, 1080)):
            r = g.Row("x", "l", "fold", "fp32", "step", h, w, h, convs=convs, macs_px=macs)
            r.p50 = fixed + o * convs + p * w * h / 1e6 + c * macs * w * h / 1e9
            rows.append(r)
    f = g.fit(rows)
    for term, want in zip(g.TERMS, (fixed, o, p, c), strict=True):
        assert f[term] == pytest.approx(want, rel=1e-6, abs=1e-9)
    assert f["max_resid_ms"] < 1e-6
    assert g.fit(rows[:3]) is None                 # one layer: the terms can't be told apart
    assert g.fit(rows[::3]) is None                # one size: likewise
    # noise that would fit a negative term keeps every term at or above zero
    noisy = rows[:6]
    for r, v in zip(noisy, (9.0, 1.0, 9.0, 1.0, 9.0, 1.0), strict=True):
        r.p50 = v
    f = g.fit(noisy)
    assert all(f[t] >= 0 for t in g.TERMS)


@pytest.mark.slow
def test_a_tiny_run_goes_end_to_end(g, tmp_path, capsys):
    out = tmp_path / "bench.json"
    assert g.main(["--device", "cpu", "--random-weights", "--layers", "conv1_1,conv1_2,conv1,conv2",
                   "--res", "32,48", "--modes", "eager,fold", "--pass", "step,forward",
                   "--n", "2", "--warm", "1", "--label", "test", "--out", str(out)]) == 0
    result = json.loads(out.read_text())
    rows = result["rows"]
    assert len(rows) == 4 * 2 * 2 * 2           # layers × sizes × modes × passes
    assert all(r["p50"] is not None and r["p50"] > 0 for r in rows), [r["note"] for r in rows]
    assert {(r["w"], r["h"]) for r in rows} == {(56, 32), (88, 48)}   # 16:9 as echo_size makes it
    assert {f["arch"] for f in result["fits"]} == {"vgg16", "googlenet"}
    assert result["label"] == "test"
    text = capsys.readouterr().out
    assert "## googlenet · fp32 · step" in text and "p ms/Mpx" in text
