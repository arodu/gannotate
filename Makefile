PREFIX ?= /usr/local
PYTHON ?= python3

.PHONY: install uninstall test

install:
	install -d "$(DESTDIR)$(PREFIX)/lib/gannotate"
	cp -a src/gannotate/. "$(DESTDIR)$(PREFIX)/lib/gannotate/"
	rm -rf "$(DESTDIR)$(PREFIX)/lib/gannotate/__pycache__"
	install -Dm755 bin/gannotate "$(DESTDIR)$(PREFIX)/bin/gannotate"
	install -Dm644 src/gannotate/data/gannotate.png \
		"$(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/gannotate.png"
	install -Dm644 data/gannotate.desktop \
		"$(DESTDIR)$(PREFIX)/share/applications/gannotate.desktop"
	-gtk-update-icon-cache -q -t "$(DESTDIR)$(PREFIX)/share/icons/hicolor" 2>/dev/null || true
	-update-desktop-database "$(DESTDIR)$(PREFIX)/share/applications" 2>/dev/null || true

uninstall:
	rm -rf "$(DESTDIR)$(PREFIX)/lib/gannotate"
	rm -f "$(DESTDIR)$(PREFIX)/bin/gannotate"
	rm -f "$(DESTDIR)$(PREFIX)/share/icons/hicolor/128x128/apps/gannotate.png"
	rm -f "$(DESTDIR)$(PREFIX)/share/applications/gannotate.desktop"
	-gtk-update-icon-cache -q -t "$(DESTDIR)$(PREFIX)/share/icons/hicolor" 2>/dev/null || true
	-update-desktop-database "$(DESTDIR)$(PREFIX)/share/applications" 2>/dev/null || true

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v
