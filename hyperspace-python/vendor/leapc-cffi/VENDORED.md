# Vendored: Ultraleap's leapc-cffi

This is the `leapc-cffi` directory of https://github.com/ultraleap/leapc-python-bindings
at commit `2341c6c3db5dc08236bb52890d8c43a224139694` (the same commit the `leap`
wrapper is pinned to in `pyproject.toml`), with the repository's Apache-2.0
`LICENSE.md` alongside. It is vendored rather than built from the git source
because upstream's `setup.py` hard-codes `libLeapC.5.dylib` on macOS, so the
build fails on Hand Tracking 6 (which ships `libLeapC.6.dylib`), and its
`cffi_build.py` links `LeapC.5`, so even with `LEAPC_LIB_OVERRIDE` the built
module asks for `libLeapC.6.dylib` while the package holds the file as `.5`.
The patch (marked "hyperspace patch" in the code): `setup.py` finds the
library as `LEAPC_LIB_OVERRIDE` if set, else the highest `libLeapC.<N>.dylib`
in `<LeapSDK>/lib`, else `libLeapC.dylib` (likewise `libLeapC.so.<N>` /
`libLeapC.so` on Linux; `LeapC.dll` on Windows as before); stages it in the
package under its own (resolved) file name, which is the name the module asks
for; and only builds when run as the setup script, so the lookup can be tested
by importing the file. `cffi_build.py` links against whatever library was
staged. `LEAPSDK_INSTALL_LOCATION` and `LEAPC_HEADER_OVERRIDE` behave as
upstream. The rest of the directory is upstream's, unchanged.
