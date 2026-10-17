import os
import re
import setuptools
import platform
import shutil

_HERE = os.path.abspath(os.path.dirname(__file__))


def get_system():
    if platform.system() == "Linux" and platform.machine() == "aarch64":
        return "Linux-ARM"
    else:
        return platform.system()


with open(os.path.join(_HERE, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

# The resource directory needs to contain the LeapC headers and libraries
_RESOURCE_DIRECTORY = os.path.join(_HERE, "src/leapc_cffi")

_OS_DEFAULT_HEADER_INSTALL_LOCATION = {
    "Windows": "C:/Program Files/Ultraleap/LeapSDK",
    "Linux": "/usr/include",
    "Linux-ARM": "/opt/ultraleap/LeapSDK",
    "Darwin": "/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK",
}

_OS_DEFAULT_LIB_INSTALL_LOCATION = {
    "Windows": _OS_DEFAULT_HEADER_INSTALL_LOCATION[get_system()],
    "Linux": "/usr/lib/ultraleap-hand-tracking-service",
    "Linux-ARM": _OS_DEFAULT_HEADER_INSTALL_LOCATION[get_system()],
    "Darwin": _OS_DEFAULT_HEADER_INSTALL_LOCATION[get_system()],
}

# hyperspace patch: the library is found by pattern rather than by one
# hard-coded name (upstream: "libLeapC.5.dylib"), so any installed Gemini
# (5, 6, ...) builds. Per OS: a regex for the versioned file names (the
# highest version wins), then the unversioned name as the fallback.
_OS_SHARED_OBJECT_VERSIONED = {
    "Windows": None,
    "Linux": r"^libLeapC\.so\.(\d+)$",
    "Linux-ARM": r"^libLeapC\.so\.(\d+)$",
    "Darwin": r"^libLeapC\.(\d+)\.dylib$",
}

_OS_SHARED_OBJECT = {
    "Windows": "LeapC.dll",
    "Linux": "libLeapC.so",
    "Linux-ARM": "libLeapC.so",
    "Darwin": "libLeapC.dylib",
}

_OS_SHARED_OBJECT_DESCRIPTION = {
    "Windows": "LeapC.dll",
    "Linux": "libLeapC.so.<N> (highest N), then libLeapC.so",
    "Linux-ARM": "libLeapC.so.<N> (highest N), then libLeapC.so",
    "Darwin": "libLeapC.<N>.dylib (highest N), then libLeapC.dylib",
}


class LeapCNotFoundError(Exception):
    pass


def _not_found_message(where, system):
    return (
        "No LeapC library found: looked for "
        + _OS_SHARED_OBJECT_DESCRIPTION[system]
        + " in "
        + str(where)
        + ". Please ensure you have Ultraleap Gemini Hand Tracking installed, or define the "
        "LEAPSDK_INSTALL_LOCATION environment variable to point to a LeapSDK directory, or "
        "LEAPC_LIB_OVERRIDE to point to the library file itself."
    )


def find_leapc_library(lib_dir, system=None):
    """The LeapC shared library to build against.

    In order: the file LEAPC_LIB_OVERRIDE names; else the versioned library in
    lib_dir with the highest version; else the unversioned one.
    """
    system = system or get_system()
    override = os.getenv("LEAPC_LIB_OVERRIDE")
    if override is not None:
        print("Library override location given, using: " + str(override))
        if not os.path.exists(override):
            raise LeapCNotFoundError(_not_found_message(override + " (LEAPC_LIB_OVERRIDE)", system))
        return override

    pattern = _OS_SHARED_OBJECT_VERSIONED[system]
    if pattern is not None and os.path.isdir(lib_dir):
        versioned = []
        for name in os.listdir(lib_dir):
            match = re.match(pattern, name)
            if match:
                versioned.append((int(match.group(1)), name))
        if versioned:
            return os.path.join(lib_dir, max(versioned)[1])

    plain = os.path.join(lib_dir, _OS_SHARED_OBJECT[system])
    if os.path.exists(plain):
        return plain

    print("Looking for LeapC library in: " + str(lib_dir))
    raise LeapCNotFoundError(_not_found_message(lib_dir, system))


def staged_library_name(libleapc_path, system=None):
    """The file name the library is staged under inside the package.

    It is the library's own name, the name the compiled module asks for at load
    time (its install name / soname), so an unversioned symlink such as
    libLeapC.dylib -> libLeapC.6.dylib is staged as libLeapC.6.dylib.
    """
    system = system or get_system()
    name = os.path.basename(libleapc_path)
    pattern = _OS_SHARED_OBJECT_VERSIONED[system]
    if pattern is not None and not re.match(pattern, name):
        real_name = os.path.basename(os.path.realpath(libleapc_path))
        if re.match(pattern, real_name):
            return real_name
    return name


def _remove_staged_libraries():
    # A library staged by an earlier build (say libLeapC.5.dylib) must not be
    # linked against instead of this build's: cffi_build.py links whatever is here.
    for name in os.listdir(_RESOURCE_DIRECTORY):
        if name.startswith("libLeapC.") or name == "LeapC.dll":
            path = os.path.join(_RESOURCE_DIRECTORY, name)
            if os.path.islink(path) or os.path.isfile(path):
                os.remove(path)


def setup_symlink(file_path, destination_path):
    if os.path.islink(destination_path):
        os.unlink(destination_path)

    if os.path.exists(destination_path):
        os.remove(destination_path)

    if os.path.exists(file_path):
        try:
            if get_system() != "Windows":
                os.symlink(file_path, destination_path)
            else:
                # Just copy it for windows, so we don't need administrator privileges
                shutil.copy(file_path, destination_path)
        except OSError as error:
            print(error)
            error_msg = (
                "Error "
                + ("creating symlink to " if get_system() != "Windows" else "copying file ")
                + file_path
                + "."
            )
            raise Exception(error_msg)
    else:
        print("Looking for LeapC library at: " + file_path)
        raise LeapCNotFoundError(_not_found_message(file_path, get_system()))


def gather_leap_sdk():
    _USER_DEFINED_INSTALL_LOCATION = os.getenv("LEAPSDK_INSTALL_LOCATION")
    _OVERRIDE_HEADER_LOCATION = os.getenv("LEAPC_HEADER_OVERRIDE")

    if _USER_DEFINED_INSTALL_LOCATION is not None:
        if get_system() == "Linux":
            print(
                "Warning: The LeapSDK directory with everything in doesn't currently exist on linux. Consider using "
                "LEAPC_HEADER_OVERRIDE and LEAPC_LIB_OVERRIDE environment variables to point to required files."
            )

        print(
            "User defined install location given, using: "
            + str(_USER_DEFINED_INSTALL_LOCATION)
            + " to generate "
            "bindings."
        )
        leapc_header_path = os.path.join(
            _USER_DEFINED_INSTALL_LOCATION,
            "include" if get_system() != "Linux" else "",
            "LeapC.h",
        )
        libleapc_dir = os.path.join(
            _USER_DEFINED_INSTALL_LOCATION,
            "lib" if get_system() != "Linux" else "",
            "x64" if get_system() == "Windows" else "",
        )
    else:
        leapc_header_path = os.path.join(
            _OS_DEFAULT_HEADER_INSTALL_LOCATION[get_system()],
            "include" if get_system() != "Linux" else "",
            "LeapC.h",
        )
        libleapc_dir = os.path.join(
            _OS_DEFAULT_LIB_INSTALL_LOCATION[get_system()],
            "lib" if get_system() != "Linux" else "",
            "x64" if get_system() == "Windows" else "",
        )

    # Override
    if _OVERRIDE_HEADER_LOCATION is not None:
        print("Header override location given, using: " + str(_OVERRIDE_HEADER_LOCATION))
        leapc_header_path = _OVERRIDE_HEADER_LOCATION

    # The library override (LEAPC_LIB_OVERRIDE) is applied by find_leapc_library
    libleapc_path = find_leapc_library(libleapc_dir)

    # Copy the found header
    if os.path.exists(leapc_header_path):
        shutil.copy(leapc_header_path, os.path.join(_RESOURCE_DIRECTORY, "LeapC.h"))
    else:
        raise Exception(
            "No LeapC.h found, please ensure you have Ultraleap Gemini Hand Tracking installed, or define "
            "LEAPSDK_INSTALL_LOCATION environment variable to point to a LeapSDK directory."
        )

    # Create a symlink for the shared object, under its own name: the name the
    # compiled module will ask for (cffi_build.py links against what is staged)
    _remove_staged_libraries()
    symlink_path = os.path.join(_RESOURCE_DIRECTORY, staged_library_name(libleapc_path))
    setup_symlink(libleapc_path, symlink_path)

    # On windows we also need to manage the LeapC.lib file
    if get_system() == "Windows":
        if _USER_DEFINED_INSTALL_LOCATION is not None:
            windows_lib_path = os.path.join(
                _USER_DEFINED_INSTALL_LOCATION, "lib", "x64", "LeapC.lib"
            )
        else:
            windows_lib_path = os.path.join(
                _OS_DEFAULT_LIB_INSTALL_LOCATION[get_system()], "lib", "x64", "LeapC.lib"
            )
        symlink_lib_path = os.path.join(_RESOURCE_DIRECTORY, "LeapC.lib")
        setup_symlink(windows_lib_path, symlink_lib_path)


# hyperspace patch: build only when run as the setup script (setuptools'
# build backend runs it as __main__), so the lookup above can be imported by
# path and tested without the SDK installed.
if __name__ == "__main__":
    gather_leap_sdk()

    setuptools.setup(
        name="leapc_cffi",
        version="0.0.1",
        author="Ultraleap",
        description="Python CFFI bindings for LeapC",
        long_description=long_description,
        long_description_content_type="text/markdown",
        package_dir={"": "src"},
        packages=setuptools.find_packages(where="src"),
        include_package_data=True,
        exclude_package_data={
            "": ["*.h", "*.lib", "scripts/*"]
        },  # Excluded from the installed package
        python_requires=">=3.8",
        setup_requires=["cffi"],
        install_requires=["cffi"],
        ext_package="leapc_cffi",  # The location that the CFFI module will be built
        cffi_modules=["src/scripts/cffi_build.py:ffibuilder"],
    )
