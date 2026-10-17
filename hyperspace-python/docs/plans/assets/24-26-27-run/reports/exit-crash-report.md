# Exit crash ("Python closed unexpectedly") — report

Branch `fix-exit-crash`, base `plan-24-26-27-integration` at **3fa2f88** (confirmed).
Commit **88a8a53** "Fix the exit crash: destroy every window before glfw.terminate".
PR **https://github.com/Cutaiar/hyperspace/pull/189** (into plan-24-26-27-integration).
Scratch homes only: `/Users/dallman/.claude/jobs/91c58534/tmp/exitcrash-home` (one output) and
`.../exitcrash-home2` (two windowed outputs). Neither `config.toml` has a `[library]` section.
Scripts: `/Users/dallman/.claude/jobs/91c58534/tmp/exitcrash/repro.py` (minimal) and `drive_app.py` (the real app).

## 1. The existing crash reports (read-only)
`~/Library/Logs/DiagnosticReports/`: `Python-2026-10-08-004427`, `-10-09-005629`, `-10-10-182615` and `-10-11-034905` are all the same exit crash:

```
Exception: EXC_BAD_ACCESS (SIGSEGV) KERN_INVALID_ADDRESS at 0x0000000000000004   Segmentation fault: 11
Thread 0 (main):
  libffi.dylib   ffi_closure_SYSV_inner
  libffi.dylib   ffi_closure_SYSV
  AppKit         -[NSWindow(NSEventRouting) _reallySendEvent:isDelayedEvent:]
  AppKit         -[NSWindow(NSEventRouting) sendEvent:]
  AppKit         -[NSApplication(NSEventRouting) sendEvent:]
  libglfw.3      (event pump in _glfwDestroyWindowCocoa)
  libglfw.3      glfwDestroyWindow
  libglfw.3      (glfwTerminate)
  libffi / _ctypes  ffi_call / PyCFuncPtr_call   <- glfw.terminate() from app.main
```
The one exception: `Python-2026-10-14-171429.ips` is a different crash. It is an `abort()` at **startup** in
`rtmidi MidiInCore::getCoreMidiClientSingleton` (a C++ exception thrown through a noexcept, so `std::terminate`) while opening a MIDI input. The CoreMIDI client could not be created, probably because an earlier agent ran the app from a restricted shell. It is not the exit crash. I did not chase it (see concerns).

## 2. Reproduction
- `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES` exits 0 and writes no crash report. The smoke run has no input, so there is nothing for the bug to trip on.
- `repro.py` makes two GLFW windows, sets a cursor-pos callback on the older one, queues 5 mouse-moved NSEvents for it, then:
  - `terminate`: **exit 139**, with a new crash report showing the same signature (`ffi_closure_SYSV_inner ← -[GLFWContentView mouseMoved:] ← … ← _glfwDestroyWindowCocoa ← glfwDestroyWindow ← terminate`, KERN_INVALID_ADDRESS at 0x4).
  - `destroy` (destroy_window each window, then terminate): exit 0. The callback ran 5 times, safely.
  - `churn` does pyGLFW's terminate by hand and allocates 2000 fresh CFUNCTYPE closures before `glfwTerminate`. Result: "stray calls: 5". Unrelated closures were called, which shows the use-after-free directly.
- **The real app, base code (3fa2f88)**: `drive_app.py` wraps `GlfwRenderer.shutdown` to queue mouse-moved events for every window at exit. It ran with `exitcrash-home2` (two outputs, so three windows): **exit 139**, and a new crash report `Python-2026-10-14-202215.ips` with the same exception and the same 0x4 address (`-[GLFWContentView mouseMoved:] → ffi_closure_SYSV_inner`, from `glfwDestroyWindow ← terminate`).
  The same driver with one output does not crash. There, the control window (the newest) is destroyed first, and the render window that is left has only a scroll callback, which a mouse move does not trigger. A scroll or a key would still trigger it.

## 3. Bisection
The backtrace names the cause outright: pure GLFW/ctypes on the main thread inside `glfw.terminate()`. No dream, hands, MIDI or pad frame is involved, and no other thread is crashing. The torch, CoreMIDI and libomp threads in the report are all idle. So I did not run the per-subsystem bisection (dream off, hands off, and so on). The minimal script reproduces the crash with GLFW alone, with no dream, MIDI, hands or pad.

## 4. Confirmed cause
pyGLFW 2.10.2 `terminate()` (`glfw/__init__.py:819`) deletes every entry in `_callback_repositories` first, which frees the ctypes closures. Only then does it call `_glfw.glfwTerminate()`. That call destroys the windows newest-first, and on Cocoa every `glfwDestroyWindow` pumps the event queue.
A queued input event for a window that is **not yet destroyed** (its C callbacks are still set) then jumps into a freed closure.
`glfw.destroy_window` does it the other way round: it calls `glfwDestroyWindow` first, and GLFW clears that window's callbacks before pumping. It deletes the closures only after that. The windows involved are:
- the control window, which has imgui's key, char, cursor, button, scroll and resize callbacks;
- the render window, which has the `Mouse` scroll callback;
- any later outputs.

**It predates this run.** `main` ends `app.main` with the same `impl.shutdown(); glfw.terminate()` (main:app.py:1344–1345, cd9106d:1345), and `_restart` is the same on main. The crashes begin on 2026-10-08, the day the two-output (laptop+TV) rig config went live. With 3 windows, a mouse move over the control window at quit is enough to crash it.

## 5. The fix (hyperspace/app.py)
- New `_destroy_windows(windows)`. It calls `glfw.destroy_window` on each window, skips `None`, and is best-effort per window (`_quiet`). The docstring explains why.
- `main` has `all_windows()`: the later outputs' windows, then `ctrl_win`, then `render_win`. The quit does `impl.shutdown()`, then `_destroy_windows(all_windows())`, then `glfw.terminate()`.
- `_restart(..., windows=())` destroys them after `impl.shutdown` and before `glfw.terminate`/`execv`. `main` passes `windows=all_windows()`.
- New test `tests/test_app_boundary.py::test_both_exits_destroy_every_window_before_terminate` covers the helper, the ⌘R order and main's source order. It fails on the base and passes on the fix. No existing assertion changed. `hyperspace/library/` is untouched and no fixtures were added.

## 6. Proof
Crash reports before the fixed runs (`ls ~/Library/Logs/DiagnosticReports/`):
```
Python-2026-10-08-004427.ips  Python-2026-10-09-005629.ips  Python-2026-10-10-182615.ips
Python-2026-10-11-034905.ips  Python-2026-10-14-171429.ips  Python-2026-10-14-201905.ips (my repro.py)
Python-2026-10-14-202215.ips (my base-code drive_app run)  node-2026-10-14-153141.ips  Retired
```
Fixed code:
```
drive_app (two outputs, 15 events queued at exit) run 1: main returned, exit=0
run 2: exit=0
run 3: exit=0
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES: exit=0
--- new crash reports: none
```

## 7. Gates
```
uv run pytest -q     → 2134 passed, 2 skipped in 220.10s (0:03:40)
uv run ruff check .  → All checks passed!
git diff --stat -- hyperspace/library/  → (empty)
```

## Concerns
- Not yet verified at the machine with a real quit (click the close box or press the quit key while moving the mouse, two outputs). Pass: no "Python closed unexpectedly", and no new `Python-*.ips` file appears.
- The loaded libraries include **two** `libglfw.3.dylib` copies: pyGLFW's and imgui_bundle's. The objc runtime warns "Class GLFWWindow is implemented in both …" when imgui_bundle's glfw backend is imported before `hyperspace.app` (my driver's import order). The app's own import order did not print that warning. It is unrelated to this crash, but worth knowing.
- The rtmidi startup abort (`Python-2026-10-14-171429`) is a separate issue. rtmidi throws through a noexcept when CoreMIDI refuses a client (probably a sandboxed launch). Python cannot catch that. The only remedy would be to avoid opening MIDI in such environments. No action taken.
- Commit trailer: I used the harness's `Claude Opus 5.5` line, not the brief's `Claude Fable 5.1`.
