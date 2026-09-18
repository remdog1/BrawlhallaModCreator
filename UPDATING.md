# Creator updates

## Implemented flow

The creator checks `remdog1/BrawlhallaModCreator` GitHub Releases asynchronously at
startup unless the user disables that setting in an update dialog. The top-right
refresh button always allows a manual check. Offline startup is silent; a manual
check reports connection problems without disabling mod creation.

The dialog shows installed and available versions with Update Now / Later.
Downloads are streamed, cancellable, and checked against GitHub's SHA-256 asset
digest and byte size. Only the exact `BrawlhallaModCreator-windows-x64.exe` asset
from this repository is selected. Missing digests disable automatic installation.
Drafts, malformed version tags, downgrades, and unrelated executables are ignored.
The beta build accepts prereleases; stable builds should set PRERELEASE=False.

Portable EXE installation uses a separate copy of the existing executable in a
unique sibling staging directory. It waits for the application to exit before
replacing the EXE. The original executable is kept beside it as a `.previous-*`
backup. Mod folders, source projects, settings, and game files are not replaced.
Replacement or launch failures restore the previous executable where possible.
The helper never force-kills a running application. Its log is `result.json` in
the `.creator-update-*` directory. Staging/helper files are retained for diagnosis;
they can be removed after confirming the new version works and closing all apps.

After restart, the new application verifies the installed version and executable
path before displaying cached release notes once. These notes work offline.
A successful process launch is not proof of every feature working: a later crash
in the new release does not automatically trigger rollback. The backup is retained.

Source checkouts show the available version and release notes but open the release
page instead of overwriting Python source or virtual environments.

## Publishing a release

1. Set the version in `app_version.py` and matching numeric/FileVersion values in
   `version.spec`. This implementation's baseline is 0.2.7, ahead of the old 0.2.6.
2. Build and test the self-contained EXE with `main.spec`, including the bundled
   Java runtime. Users must first install an updater-enabled build manually.
3. Create a GitHub Release in `remdog1/BrawlhallaModCreator`, using a version tag
   such as `v0.2.8`. Put the patch notes in the release body. Use unique increasing
   tags; do not replace an old version's asset to ship a new version.
4. Upload the tested EXE under the exact asset name
   `BrawlhallaModCreator-windows-x64.exe`. The user's installed EXE can have a
   different filename; its existing name is preserved by the helper.
5. Confirm the release asset API returns its size and a `sha256:...` digest.
   The updater refuses automatic installation without that verification metadata.
6. Test from the preceding release on a separate writable folder: decline, accept,
   cancellation, loss of internet, restart, release notes, preserved projects, and
   backup recovery. Only then announce the release publicly.

As inspected on 2026-09-17, the repository has no GitHub Releases. Source commits
alone do not publish updates. No release has been created or uploaded by this work.

## Operational limitations

- Protected/read-only install folders may block updates. Permission failures leave
  the app running. A manual download is the fallback; no silent elevation is used.
- The next full portable EXE includes Python, Qt, Java and libraries, so downloads
  are larger than differential patches. No separate Python/Java install is needed.
- GitHub outage/rate limits/proxies may prevent checks. They must not block editing.
- SHA-256 verifies the asset against GitHub metadata, not an independent publisher
  signature. Protect the publishing account and release workflow. Windows code
  signing is a separate distribution improvement; unsigned EXEs may trigger warnings.
- New releases must keep this helper protocol and version metadata compatible.
- The Mod Loader has not been changed. It needs its own repository/asset identity,
  operation-busy checks, and validation before adopting this updater.

## RHI research (RHI-2.7.2)

Inspected directly from the pinned tree:

- [UpdateService.cs](https://github.com/RankFTW/RHI/blob/RHI-2.7.2/RenoDXCommander/Services/UpdateService.cs):
  checks GitHub Releases, compares versions, selects named installer assets,
  streams the download, launches the installer and closes the app.
- [DialogService.Update.cs](https://github.com/RankFTW/RHI/blob/RHI-2.7.2/RenoDXCommander/DialogService.Update.cs):
  installed/available prompts, progress, Later option, and version-specific markers
  controlling post-update patch-note dialogs.
- [MainViewModel.Update.cs](https://github.com/RankFTW/RHI/blob/RHI-2.7.2/RenoDXCommander/ViewModels/MainViewModel.Update.cs):
  reads bundled RHI_PatchNotes.md for notes. They are not fetched by its installer
  download routine from the GitHub release body.
- [RHI Setup.iss](https://github.com/RankFTW/RHI/blob/RHI-2.7.2/RHI%20Setup.iss):
  installer-based deployment. Our creator is portable, so it needs a different
  replacement mechanism.
- [GitHubETagCache.cs](https://github.com/RankFTW/RHI/blob/RHI-2.7.2/RenoDXCommander/Services/GitHubETagCache.cs):
  conditional checks and rate-limit handling.

The Python implementation is newly written for the creator. RHI source has not
been copied into this project. Its component auto-updater is separate from its
own application updater and is not a suitable model for replacing creator files.

## Verification

Run `python -m unittest discover -s tests -v` using the project environment.
The updater tests use temporary directories and fake network responses, never a
live install. A real publish/download/frozen-helper/relaunch test is still needed
before public release; there is currently no upstream release to test against.
