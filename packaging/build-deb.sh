#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "error: dpkg-deb not found" >&2
    echo "Build on Debian/Ubuntu or use the package CI workflow." >&2
    exit 1
fi

VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' src/gannotate/__init__.py)"
PYPROJECT_VERSION="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)"
if [ -z "$VERSION" ]; then
    echo "error: could not read version from src/gannotate/__init__.py" >&2
    exit 1
fi
if [ "$VERSION" != "$PYPROJECT_VERSION" ]; then
    echo "error: version mismatch (__init__.py=$VERSION, pyproject.toml=$PYPROJECT_VERSION)" >&2
    exit 1
fi

PKGNAME="gannotate"
ARCH="all"
REVISION="${DEB_REVISION:-1}"
DEB_VERSION="${VERSION}-${REVISION}"
MAINTAINER="${DEB_MAINTAINER:-Alberto Rodriguez <arodu.dev@gmail.com>}"

BUILD_DIR="$ROOT/build/deb"
PKGROOT="$BUILD_DIR/pkgroot"
OUT_DIR="$ROOT/dist"
OUT="$OUT_DIR/${PKGNAME}_${DEB_VERSION}_${ARCH}.deb"

rm -rf "$BUILD_DIR"
mkdir -p "$PKGROOT" "$OUT_DIR"

make install DESTDIR="$PKGROOT" PREFIX=/usr
rm -f "$PKGROOT/usr/share/icons/hicolor/icon-theme.cache"
rm -f "$PKGROOT/usr/share/applications/mimeinfo.cache"

mkdir -p "$PKGROOT/usr/share/doc/$PKGNAME"
cat > "$PKGROOT/usr/share/doc/$PKGNAME/copyright" <<COPYRIGHT
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: $PKGNAME
Source: https://github.com/arodu/gannotate
Files: *
Copyright: 2026 Alberto Rodriguez <arodu.dev@gmail.com>
License: GPL-3+
 On Debian systems, the complete text of the GNU General Public License
 version 3 can be found in /usr/share/common-licenses/GPL-3.
COPYRIGHT
install -Dm644 LICENSE "$PKGROOT/usr/share/doc/$PKGNAME/LICENSE"

cat > "$BUILD_DIR/changelog.Debian" <<CHANGELOG
$PKGNAME ($DEB_VERSION) unstable; urgency=medium

  * Release $VERSION.

 -- $MAINTAINER  $(LC_ALL=C date -R)
CHANGELOG
gzip -9n -c "$BUILD_DIR/changelog.Debian" > "$PKGROOT/usr/share/doc/$PKGNAME/changelog.Debian.gz"
chmod 644 "$PKGROOT/usr/share/doc/$PKGNAME/changelog.Debian.gz"

INSTALLED_SIZE="$(du -sk "$PKGROOT" | cut -f1)"

mkdir -p "$PKGROOT/DEBIAN"
cat > "$PKGROOT/DEBIAN/control" <<CONTROL
Package: $PKGNAME
Version: $DEB_VERSION
Architecture: $ARCH
Maintainer: $MAINTAINER
Installed-Size: $INSTALLED_SIZE
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, python3-cairo, librsvg2-common
Recommends: libnotify-bin
Suggests: xfce4-screenshooter
Section: graphics
Priority: optional
Homepage: https://github.com/arodu/gannotate
Description: lightweight GTK3 screenshot annotator
 Gannotate opens an existing screenshot and lets you add arrows,
 rectangles, ellipses, lines, pencil strokes, highlights and text.
 .
 It can save the annotated image as PNG, copy it to the clipboard, or
 run a configurable upload command.
CONTROL

(
    cd "$PKGROOT"
    find usr -type f -print0 | sort -z | xargs -0 md5sum > DEBIAN/md5sums
)

dpkg-deb --build --root-owner-group "$PKGROOT" "$OUT"
echo "$OUT"
