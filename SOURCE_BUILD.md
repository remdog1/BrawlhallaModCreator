# Source and release builds

The maintained core is included directly under `core/`. It was originally based
on https://github.com/bucccket/BhModLoaderCore; the old submodule pointer no longer
represented the local creator fixes. Existing author credits and licenses remain.

User mods, mod sources, virtual environments, build output, caches, and local Java
installations are not part of this repository. The release EXE is distributed as
a GitHub Release asset, not a file committed to Git.

## Windows development

Use 64-bit Python 3.13 and a project virtual environment:

```bat
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Place a complete 64-bit Windows Java 17 JRE in `runtime/jre17`, including its
`release` file, `bin/server/jvm.dll`, libraries and licenses. Do not copy just the
DLL. The current tested runtime is Eclipse Temurin 17.0.19+10. Java stays local
for development and is included in the self-contained release executable.

Run `Start Creator.cmd`. The game must be installed for normal creator workflows.

## Tests and packaging

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip install PyInstaller
.venv\Scripts\python.exe -m PyInstaller --noconfirm main.spec
```

The spec validates the JVM against the build environment before packaging.
To include the opt-in Java binary round-trip test, set `CREATOR_JAVA_TESTS=1`.
Use a copy of the executable in an isolated folder for update/restart testing.
See `UPDATING.md` for release asset naming and publishing requirements.
