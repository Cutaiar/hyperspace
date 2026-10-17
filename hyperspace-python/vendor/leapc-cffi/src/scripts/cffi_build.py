"""Build script for the LeapC CFFI module

This script should never be imported directly, and only used by the package
setup.py
"""

import os
import platform

from cffi import FFI

_HERE = os.path.abspath(os.path.dirname(__file__))

# The resource directory needs to contain the LeapC headers and libraries
_RESOURCE_DIRECTORY = os.path.join(_HERE, "..", "leapc_cffi")


def sanitise_leapc_header(input_str):
    """Sanitise the LeapC Header so that it can be used as a cdef string in cffi"""
    lines = input_str.split("\n")

    # Some '#define' statements define numbers which need to be replaced in the header
    value_defines = {"LEAP_DISTORTION_MATRIX_N": None}
    for line in lines:
        if line.startswith("#define"):
            split_line = line.split(" ")
            key = split_line[1]
            if key in value_defines:
                value_defines[key] = split_line[2]

    header_replacements = {"LEAP_CALL": "", "LEAP_EXPORT": ""}
    header_replacements.update(value_defines)

    new_lines = []
    for line in lines:
        for key, val in header_replacements.items():
            line = line.replace(key, val)
        new_lines.append(line)
    lines = new_lines

    # Remove all lines that start with #
    # Remove anything that's in an #if statement (except the top level '#ifndef _LEAP_C_H')
    #   This allows us to remove lines like the closing bracket of '#extern "C"{'
    #   and lines such as 'typedef __int32 int32_t'
    new_lines = []
    if_depth = 0
    for line in lines:
        if line.startswith("#"):
            no_spaced_line = line.replace(" ", "")[1:]
            if no_spaced_line.startswith("if"):
                if_depth += 1
            elif no_spaced_line.startswith("endif"):
                if_depth -= 1
        elif if_depth == 1:
            new_lines.append(line)

    lines = new_lines

    ignored_line_beginnings = [
        "LEAP_STATIC_ASSERT",
    ]

    new_lines = []
    for line in lines:
        include_line = True
        for beginning in ignored_line_beginnings:
            if line.startswith(beginning):
                include_line = False
                break
        if include_line:
            new_lines.append(line)

    return "\n".join(new_lines)


leapc_header_fpath = os.path.join(_RESOURCE_DIRECTORY, "LeapC.h")
with open(leapc_header_fpath) as fp:
    leapc_header = fp.read()

cffi_cdef = sanitise_leapc_header(leapc_header)

ffibuilder = FFI()
ffibuilder.cdef(cffi_cdef, packed=True)

cffi_src_fpath = os.path.join(os.path.dirname(__file__), "cffi_src.h")
with open(cffi_src_fpath) as fp:
    cffi_src = fp.read()

extra_link_args = {
    "Windows": [],
    "Linux": ["-Wl,-rpath=$ORIGIN"],
    "Darwin": ["-Wl,-rpath,@loader_path"],
}


def staged_library():
    """hyperspace patch: link against the library setup.py staged, by its own
    name (upstream hard-coded "LeapC.5" on Darwin), so the compiled module asks
    for the file that sits beside it in the package."""
    if platform.system() == "Windows":
        return ["LeapC"]
    for name in sorted(os.listdir(_RESOURCE_DIRECTORY)):
        if platform.system() == "Darwin" and name.startswith("lib") and name.endswith(".dylib"):
            return [name[len("lib"):-len(".dylib")]]  # libLeapC.6.dylib -> LeapC.6
        if platform.system() == "Linux" and name.startswith("libLeapC.so"):
            # libLeapC.so -> LeapC; libLeapC.so.6 -> :libLeapC.so.6 (GNU ld's exact name)
            return ["LeapC"] if name == "libLeapC.so" else [":" + name]
    raise Exception("No staged LeapC library in " + _RESOURCE_DIRECTORY + " (run via setup.py)")


ffibuilder.set_source(
    "_leapc_cffi",
    cffi_src,
    libraries=staged_library(),
    include_dirs=[_RESOURCE_DIRECTORY],
    library_dirs=[_RESOURCE_DIRECTORY],
    extra_link_args=extra_link_args[platform.system()],
)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
