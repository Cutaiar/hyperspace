"""The time-by-param lint: does a shader multiply a time by a param?

The rule (the owner, 2026-11-02; DECISIONS "Effects and the look-back"):
**no shader multiplies time by a param**. `u_phase * u_drift` reads as a
rate, but the shader sees the integrated phase, so a knob step of
Δdrift shifts the field by `phase × Δdrift` — whole screens, hours into a
set. A rate-like param is integrated by the host (`// @clock` in fx.py,
`Renderer._pattern_clock` for the patterns) and the shader reads the
phase. `tests/test_shader_time_lint.py` runs this over every shipped
shader; this module is the detector.

What counts, exactly:

- a **time symbol** is a time uniform (`u_time`, `u_phase`, the patterns'
  `u_ptime`), an effect's `@clock` uniforms, and any local assigned from
  an expression that carries one (`float t = u_phase;`, `float T =
  u_phase * 20.0;`) — through `+`, `-`, `*`, `/`, parentheses, the vector
  constructors (`vec2(t)` is still t) and a user function's return;
- a **param symbol** is a param uniform (an effect's `@param`s; the
  patterns' `u_mod`) and any local or user function that carries one the
  same way (`m_speed()` returns `u_mod[3]`, so it is a param);
- a **finding** is a `*`, `/` (time on the left), `*=` or `/=` with a time
  symbol on one side and a param symbol on the other.

What does not count: a param scaling a *function* of time — `u_amount *
sin(u_phase)` is an amplitude, bounded whatever the phase, so every call
but a constructor is opaque (its result carries no taint, and its
arguments are checked on their own). `u_phase + u_param` is a phase
offset, not a rate. `mod(u_phase, u_param)` is a wrap. A hash of a cell
(`hash22(cell).y`) is not a param, so glimmer's per-cell rates pass:
their grid re-hashes on a size step, which is another rule's business.

The analysis is a small recursive descent over the shader's tokens, one
function body at a time, with a flat scope per function; formal
parameters take the taint of every call site's arguments (fractals'
`shape(uv, T)` sees `T` as a time), to a fixpoint. It is a net for the
shaders we ship, not a GLSL compiler: a construct it does not know is
skipped to the next `;`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

TIME_UNIFORMS = frozenset({"u_time", "u_phase", "u_ptime"})
CONSTRUCTORS = frozenset({
    "float", "int", "uint", "bool", "vec2", "vec3", "vec4", "ivec2", "ivec3", "ivec4",
    "uvec2", "uvec3", "uvec4", "bvec2", "bvec3", "bvec4", "mat2", "mat3", "mat4",
})
TYPES = CONSTRUCTORS | {"void", "sampler2D"}
QUALIFIERS = frozenset({"const", "uniform", "in", "out", "inout", "highp", "mediump", "lowp",
                        "flat", "precision"})
ASSIGN_OPS = frozenset({"=", "+=", "-=", "*=", "/="})

_TOKEN = re.compile(r"""
    (?P<num>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?[uUfF]?)
  | (?P<id>[A-Za-z_]\w*)
  | (?P<op>\+=|-=|\*=|/=|\+\+|--|==|!=|<=|>=|&&|\|\||<<|>>|[-+*/<>=!?:,;.(){}\[\]%^&|~])
  | (?P<ws>\s+)
  | (?P<bad>.)
""", re.VERBOSE)


@dataclass(frozen=True)
class Token:
    kind: str       # num | id | op
    text: str
    line: int


@dataclass(frozen=True)
class Taint:
    """What an expression carries: the time symbols and the param symbols
    in it (by their uniform or function name, never a local alias)."""

    times: frozenset[str] = frozenset()
    params: frozenset[str] = frozenset()

    def __or__(self, other: Taint) -> Taint:
        return Taint(self.times | other.times, self.params | other.params)

    def __bool__(self) -> bool:
        return bool(self.times or self.params)


NONE = Taint()


@dataclass(frozen=True)
class Finding:
    """One product of a time and a param: where, which time symbols and
    which param symbols (the params on the side opposite the time)."""

    line: int
    times: frozenset[str]
    params: frozenset[str]


def strip(source: str) -> str:
    """Comments and preprocessor lines gone, every line kept (numbers hold)."""
    source = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group()), source, flags=re.DOTALL)
    out = []
    for line in source.split("\n"):
        line = line.split("//", 1)[0]
        if line.lstrip().startswith("#"):
            line = ""
        out.append(line)
    return "\n".join(out)


def tokenize(source: str) -> list[Token]:
    toks: list[Token] = []
    line = 1
    for m in _TOKEN.finditer(strip(source)):
        kind = m.lastgroup
        text = m.group()
        if kind == "ws":
            line += text.count("\n")
            continue
        if kind == "bad":
            continue
        toks.append(Token(kind, text, line))
    return toks


@dataclass
class Func:
    name: str
    formals: list[str]
    start: int          # index of the body's `{`
    end: int            # index just past the body's `}`


class _Parser:
    """One pass over the functions of a shader with given formal taints.

    `names` is the flat scope of the function being read; `calls` collects
    each user function's argument taints by position and `returns` what
    each returns, for the next round."""

    def __init__(self, toks: list[Token], funcs: dict[str, Func],
                 globals_: dict[str, Taint], formal_taints: dict[str, list[Taint]],
                 returns: dict[str, Taint]):
        self.toks = toks
        self.funcs = funcs
        self.globals = globals_
        self.formal_taints = formal_taints
        self.returns_in = returns
        self.names: dict[str, Taint] = {}
        self.i = 0
        self.end = 0
        self.findings: set[Finding] = set()
        self.calls: dict[str, list[Taint]] = defaultdict(list)
        self.returns: dict[str, Taint] = {}
        self.current = ""

    # ---- tokens ----

    def peek(self, k: int = 0) -> Token | None:
        j = self.i + k
        return self.toks[j] if j < self.end else None

    def at(self, text: str, k: int = 0) -> bool:
        t = self.peek(k)
        return t is not None and t.text == text

    def take(self) -> Token:
        t = self.toks[self.i]
        self.i += 1
        return t

    def expect(self, text: str) -> None:
        if self.at(text):
            self.i += 1

    def skip_past(self, text: str) -> None:
        """To just past the next `text` at depth 0 (or the end)."""
        depth = 0
        while self.i < self.end:
            t = self.take()
            if t.text in "([{":
                depth += 1
            elif t.text in ")]}":
                depth -= 1
            if t.text == text and depth <= 0:
                return

    # ---- a function ----

    def run(self, f: Func) -> None:
        self.current = f.name
        self.names = dict(self.globals)
        for k, formal in enumerate(f.formals):
            taints = self.formal_taints.get(f.name, [])
            self.names[formal] = taints[k] if k < len(taints) else NONE
        self.i, self.end = f.start, f.end
        self.returns[f.name] = NONE
        while self.i < self.end:
            self.statement()

    def statement(self) -> None:
        t = self.peek()
        if t is None:
            return
        if t.text in "{};":
            self.i += 1
            return
        if t.kind == "id":
            if t.text in ("if", "while", "switch"):
                self.i += 1
                self.paren_expr()
                return
            if t.text == "else":
                self.i += 1
                return
            if t.text == "for":
                self.i += 1
                self.expect("(")
                self.statement()                      # the init, through its `;`
                if not self.at(";"):
                    self.expr()
                self.expect(";")
                if not self.at(")"):
                    self.expr()
                    while self.at(","):
                        self.i += 1
                        self.expr()
                self.expect(")")
                return
            if t.text == "return":
                self.i += 1
                if not self.at(";"):
                    self.returns[self.current] = self.returns[self.current] | self.expr()
                self.skip_past(";")
                return
            if t.text in ("break", "continue", "discard"):
                self.skip_past(";")
                return
            if t.text in QUALIFIERS or (t.text in TYPES and self.peek(1) is not None
                                        and self.peek(1).kind == "id"):
                self.declaration()
                return
        self.assignment_or_expr()
        self.skip_past(";")

    def paren_expr(self) -> Taint:
        self.expect("(")
        taint = self.expr() if not self.at(")") else NONE
        self.skip_past(")")
        return taint

    def declaration(self) -> None:
        if self.at("uniform"):              # a uniform keeps the taint it was given
            self.skip_past(";")
            return
        while self.peek() is not None and self.peek().text in QUALIFIERS:
            self.i += 1
        self.i += 1                                   # the type
        if self.at("["):
            self.skip_past("]")
        while self.i < self.end:
            name_tok = self.peek()
            if name_tok is None or name_tok.kind != "id":
                self.skip_past(";")
                return
            self.i += 1
            if self.at("["):
                self.skip_past("]")
            taint = NONE
            if self.at("="):
                self.i += 1
                taint = self.expr()
            self.names[name_tok.text] = taint
            if self.at(","):
                self.i += 1
                continue
            self.skip_past(";")
            return

    def assignment_or_expr(self) -> None:
        t = self.peek()
        if t is not None and t.kind == "id":
            # `name [.x | [i]]* op= expr`
            j = 1
            while True:
                if self.at(".", j) and self.peek(j + 1) is not None:
                    j += 2
                elif self.at("[", j):
                    depth = 0
                    while self.peek(j) is not None:
                        if self.at("[", j):
                            depth += 1
                        elif self.at("]", j):
                            depth -= 1
                            if depth == 0:
                                j += 1
                                break
                        j += 1
                else:
                    break
            op = self.peek(j)
            if op is not None and op.text in ASSIGN_OPS:
                self.i += j + 1
                rhs = self.expr()
                have = self.names.get(t.text, NONE)
                if op.text in ("*=", "/="):
                    self.check(have, rhs, op)
                self.names[t.text] = rhs if op.text == "=" and j == 1 else have | rhs
                return
        self.expr()

    # ---- expressions ----

    def expr(self) -> Taint:
        taint = self.binary(0)
        if self.at("?"):
            self.i += 1
            a = self.expr()
            self.expect(":")
            b = self.expr()
            return a | b
        return taint

    _LEVELS = (
        {"||"}, {"&&"}, {"|"}, {"^"}, {"&"}, {"==", "!="}, {"<", ">", "<=", ">="},
        {"<<", ">>"}, {"+", "-"}, {"*", "/", "%"},
    )

    def binary(self, level: int) -> Taint:
        if level == len(self._LEVELS):
            return self.unary()
        ops = self._LEVELS[level]
        left = self.binary(level + 1)
        while self.peek() is not None and self.peek().text in ops:
            op = self.take()
            right = self.binary(level + 1)
            if op.text in ("*", "/", "%"):
                self.check(left, right, op)
                left = left | right
            elif op.text in ("+", "-"):
                left = left | right
            else:
                left = NONE                          # a comparison, a logical: a bool
        return left

    def unary(self) -> Taint:
        if self.peek() is not None and self.peek().text in ("-", "+", "!", "~", "++", "--"):
            self.i += 1
            return self.unary()
        return self.postfix()

    def postfix(self) -> Taint:
        taint = self.primary()
        while True:
            if self.at("."):
                self.i += 2                           # a swizzle: the base's taint
            elif self.at("["):
                self.i += 1
                self.expr()
                self.expect("]")
            elif self.at("++") or self.at("--"):
                self.i += 1
            else:
                return taint

    def primary(self) -> Taint:
        t = self.peek()
        if t is None:
            return NONE
        if t.text == "(":
            self.i += 1
            taint = self.expr()
            self.expect(")")
            return taint
        self.i += 1
        if t.kind == "num":
            return NONE
        if t.kind != "id":
            return NONE
        if self.at("("):
            self.i += 1
            args: list[Taint] = []
            if not self.at(")"):
                args.append(self.expr())
                while self.at(","):
                    self.i += 1
                    args.append(self.expr())
            self.expect(")")
            if t.text in CONSTRUCTORS:
                out = NONE
                for a in args:
                    out = out | a
                return out
            if t.text in self.funcs:
                have = self.calls[t.text]
                for k, a in enumerate(args):
                    if k < len(have):
                        have[k] = have[k] | a
                    else:
                        have.append(a)
                # what it returns, and its own name when that is a param
                # symbol (the patterns' accessors, `m_colour()`)
                return self.returns_in.get(t.text, NONE) | self.globals.get(t.text, NONE)
            return NONE                               # a built-in: opaque
        return self.names.get(t.text, NONE)

    def check(self, left: Taint, right: Taint, op: Token) -> None:
        if left.times and right.params:
            self.findings.add(Finding(op.line, left.times, right.params))
        if op.text == "*" and right.times and left.params:
            self.findings.add(Finding(op.line, right.times, left.params))


def _functions(toks: list[Token]) -> tuple[dict[str, Func], list[tuple[int, int]]]:
    """Every function definition (name, formals, body range) and the ranges
    of the top-level statements between them."""
    funcs: dict[str, Func] = {}
    tops: list[tuple[int, int]] = []
    i, n = 0, len(toks)
    while i < n:
        # `type name ( … ) {`
        if (toks[i].kind == "id" and i + 2 < n and toks[i + 1].kind == "id"
                and toks[i + 2].text == "("):
            j = i + 3
            depth = 1
            formals: list[str] = []
            last: Token | None = None
            while j < n and depth:
                if toks[j].text == "(":
                    depth += 1
                elif toks[j].text == ")":
                    depth -= 1
                elif toks[j].text == "," and last is not None:
                    formals.append(last.text)
                if toks[j].kind == "id":
                    last = toks[j]
                j += 1
            if last is not None and (not formals or formals[-1] != last.text):
                formals.append(last.text)
            if j < n and toks[j].text == "{":
                start = j
                depth = 0
                while j < n:
                    if toks[j].text == "{":
                        depth += 1
                    elif toks[j].text == "}":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
                formals = [f for f in formals if f not in TYPES and f not in QUALIFIERS]
                funcs[toks[i + 1].text] = Func(toks[i + 1].text, formals, start, j)
                i = j
                continue
            if j < n and toks[j].text == ";":            # a prototype
                i = j + 1
                continue
        # a top-level statement: to its `;`
        j = i
        while j < n and toks[j].text != ";":
            j += 1
        tops.append((i, j + 1))
        i = j + 1
    return funcs, tops


def findings(source: str, params: set[str], times: set[str] = TIME_UNIFORMS,
             rounds: int = 6) -> set[Finding]:
    """Every time × param product in `source`: `params` are its param
    symbols (uniform names), `times` its time symbols."""
    toks = tokenize(source)
    funcs, tops = _functions(toks)
    globals_: dict[str, Taint] = {t: Taint(times=frozenset({t})) for t in times}
    globals_.update({p: Taint(params=frozenset({p})) for p in params})
    # top-level declarations (constants) read with the uniforms' taints
    top = _Parser(toks, funcs, globals_, {}, {})
    for start, end in tops:
        top.i, top.end = start, end
        top.names = globals_
        top.statement()
    formal_taints: dict[str, list[Taint]] = {}
    returns: dict[str, Taint] = {}
    out: set[Finding] = set()
    for _ in range(rounds):
        p = _Parser(toks, funcs, globals_, formal_taints, returns)
        for f in funcs.values():
            p.run(f)
        out = p.findings
        new_formals = {name: list(t) for name, t in p.calls.items()}
        if new_formals == formal_taints and p.returns == returns:
            break
        formal_taints, returns = new_formals, p.returns
    return out
