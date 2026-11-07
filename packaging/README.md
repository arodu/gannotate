# Packaging

Gannotate ships as a Debian package (`.deb`) and an Arch package
(`PKGBUILD`). Both use the existing `Makefile` to install into a staging
directory, so the installed layout stays identical to `make install`.

## Version checklist

Before creating the release tag, keep these in sync:

- `pyproject.toml`
- `src/gannotate/__init__.py`
- `CHANGELOG.md`
- `packaging/PKGBUILD` (`pkgver`)
- the tag name (`v0.2.0`)

## Debian / Ubuntu

`build-deb.sh` reads the version from `src/gannotate/__init__.py`, stages the
application with `make install`, and runs `dpkg-deb`:

```sh
./packaging/build-deb.sh
```

The output is `dist/gannotate_<version>-1_all.deb`. The script requires
`dpkg-deb` and `make`. On Arch/Manjaro, build it in Docker:

```sh
docker run --rm -v "$PWD:/src" -w /src \
  -e UID="$(id -u)" -e GID="$(id -g)" ubuntu:24.04 bash -c '
    apt-get update
    apt-get install -y --no-install-recommends make dpkg-dev
    ./packaging/build-deb.sh
    chown -R "$UID:$GID" build dist
  '
```

Test the result in a clean Debian/Ubuntu container with:

```sh
sudo apt install ./dist/gannotate_<version>-1_all.deb
gannotate
```

Use `DEB_REVISION` to change the Debian revision and `DEB_MAINTAINER` to
override the maintainer field.

## Arch / Manjaro

`PKGBUILD` points at the GitHub tag tarball. After the `v0.2.0` tag exists,
update the checksum and generate `.SRCINFO`:

```sh
cd packaging
updpkgsums
makepkg --printsrcinfo > .SRCINFO
makepkg -si
```

`updpkgsums` comes from `pacman-contrib`. Until the tag is published, the
recipe contains `sha256sums=('SKIP')`; update it before publishing to the AUR.

To publish, copy `PKGBUILD` and `.SRCINFO` into the AUR repository for
`gannotate` and push. Users then install with `yay -S gannotate` or
`pamac build gannotate`.

## Release CI

`.github/workflows/package.yml` builds the `.deb` on every push to `main`,
pull request and tag. On tags matching `v*` it also:

1. calls the reusable `tests.yml` workflow; if tests fail, the release is not
   published;
2. runs `lintian --fail-on error`;
3. generates `dist/SHA256SUMS`;
4. creates the GitHub release if needed and uploads the `.deb` and checksums
   using `GITHUB_TOKEN`.

The `deb` job uploads a temporary `gannotate-deb` artifact on every run. To
test it before tagging, open the workflow run in **Actions → packages →
Artifacts**, or download it with the GitHub CLI:

```sh
gh run list --workflow=package.yml
gh run download <run-id> -n gannotate-deb
```

The web UI downloads a zip containing the `.deb` and `SHA256SUMS`; `gh run
download` extracts it into a directory. Artifacts expire after 90 days by
default; release assets are permanent.

`tests.yml` runs on branch pushes and pull requests. Tag pushes skip it as a
standalone workflow and run it through the reusable call in `package.yml`, so
tests are not duplicated.

The Arch package is not built in CI because it requires an Arch environment.
Build it locally (see above) or in an Arch container before updating the AUR.
