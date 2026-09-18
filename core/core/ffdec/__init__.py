import os
import sys
import jpype

__all__ = []
BUILD_SAFE_IMPORT = os.environ.get("BMOD_PYINSTALLER_ANALYSIS") == "1"
_dll_directory_handles = []


def _resourcePath(*parts):
    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    basePath = getattr(sys, "_MEIPASS", app_root)
    return os.path.abspath(os.path.join(basePath, *parts))


def prepare_jvm_dll_dirs(jvm_path):
    jvm_dir = os.path.dirname(jvm_path)
    java_bin_dir = os.path.abspath(os.path.join(jvm_dir, ".."))

    for dll_dir in (java_bin_dir, jvm_dir):
        if not os.path.isdir(dll_dir):
            continue

        if hasattr(os, "add_dll_directory"):
            _dll_directory_handles.append(os.add_dll_directory(dll_dir))

        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        if dll_dir not in path_parts:
            os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")


def java_major_version(jvm_path):
    runtime_root = os.path.abspath(os.path.join(os.path.dirname(jvm_path), "..", ".."))
    release_file = os.path.join(runtime_root, "release")

    try:
        with open(release_file, "r", encoding="utf-8") as file:
            for line in file:
                if not line.startswith("JAVA_VERSION="):
                    continue

                version = line.split("=", 1)[1].strip().strip('"')
                major = version.split(".", 1)[0]
                if major == "1":
                    major = version.split(".")[1]
                return int(major)
    except (OSError, ValueError, IndexError):
        return 0

    return 0


def jvm_start_args(jvm_path, *memory_args):
    args = list(memory_args)

    if java_major_version(jvm_path) >= 22:
        args.append("--enable-native-access=ALL-UNNAMED")

    return args


def minimum_java_major():
    version = getattr(jpype, "__version__", "1.7")

    try:
        major, minor, patch = (int(part) for part in version.split(".", 2)[0:3])
    except ValueError:
        return 11

    if (major, minor, patch) <= (1, 5, 2):
        return 8

    return 11


PLAYERGLOBAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "playerglobal32_0.swc"))
FFDEC_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "ffdec_lib.jar"))
CMYKJPEG_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "cmykjpeg.jar"))
JL_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "jl1.0.1.jar"))


def ffdec_classpath():
    classpath = [FFDEC_LIB]
    lib_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "lib"))

    if os.path.isdir(lib_folder):
        for file_name in sorted(os.listdir(lib_folder)):
            if not file_name.lower().endswith(".jar"):
                continue

            jar_path = os.path.join(lib_folder, file_name)
            if jar_path not in classpath:
                classpath.append(jar_path)

    for jar_path in (CMYKJPEG_LIB, JL_LIB):
        if jar_path not in classpath:
            classpath.append(jar_path)

    return classpath

assert os.path.exists(FFDEC_LIB), "ffdec_lib.jar doesn't exist"
assert os.path.exists(CMYKJPEG_LIB), "cmykjpeg.jar doesn't exist"
assert os.path.exists(JL_LIB), "jl1.0.1.jar doesn't exist"

FFDEC_CLASSPATH = ffdec_classpath()

jvmpath = None

if sys.platform.startswith("win"):
    minJavaMajor = minimum_java_major()

    for bundledJvmPath in (
        _resourcePath("runtime", "jre17", "bin", "server", "jvm.dll"),
        _resourcePath("runtime", "jre", "bin", "server", "jvm.dll"),
        _resourcePath("jre17", "bin", "server", "jvm.dll"),
        _resourcePath("jre", "bin", "server", "jvm.dll"),
    ):
        if os.path.exists(bundledJvmPath) and java_major_version(bundledJvmPath) >= minJavaMajor:
            prepare_jvm_dll_dirs(bundledJvmPath)
            jvmpath = bundledJvmPath
            break

    if jvmpath is None and not getattr(sys, "frozen", False):
        try:
            system_jvm = jpype.getDefaultJVMPath()
            if java_major_version(system_jvm) >= minJavaMajor:
                prepare_jvm_dll_dirs(system_jvm)
                jvmpath = system_jvm
        except jpype._jvmfinder.JVMNotFoundException:
            pass

    if not BUILD_SAFE_IMPORT:
        flashlibFolder = os.path.join(os.getenv("APPDATA"), "JPEXS", "FFDec", "flashlib")
        flashlibFile = os.path.join(flashlibFolder, "playerglobal32_0.swc")

        if not os.path.exists(flashlibFile):
            if not os.path.exists(flashlibFolder):
                os.makedirs(flashlibFolder, exist_ok=True)

            with open(PLAYERGLOBAL, "rb") as orig:
                with open(flashlibFile, "wb") as new:
                    new.write(orig.read())

elif sys.platform == "darwin":
    jvmpath = "/Library/Internet Plug-Ins/JavaAppletPlugin.plugin/Contents/Home/lib/jli/libjli.dylib"

else:
    pass

if BUILD_SAFE_IMPORT and jvmpath is None:
    jvmpath = "build-safe-placeholder"

if jvmpath is None:
    if getattr(sys, "frozen", False):
        raise ImportError("The creator's bundled Java runtime is missing or incompatible. "
                          "Use a complete build containing runtime/jre17; no separate Java installation is needed.")
    raise ImportError("Java not found!")

if not BUILD_SAFE_IMPORT and not jpype.isJVMStarted():
    jpype.startJVM(jvmpath, *jvm_start_args(jvmpath, "-Xmx1024m", "-Xms128m"), classpath=FFDEC_CLASSPATH)



from .classes import *
