"""Step 6: Final decision view (Try Live vs Install to Disk) for LSD-Welcome."""

from __future__ import annotations

import subprocess
from typing import Callable, Any

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = object  # type: ignore


class DecisionView(Gtk.Box):  # type: ignore
    """Step 6: Action cards for trying LSD_OS live or launching Calamares installer."""

    def __init__(self, headless: bool = False, **kwargs: Any) -> None:
        self._headless = headless or not GTK_AVAILABLE
        self._quit_callbacks: list[Callable[[], None]] = []

        if self._headless:
            return

        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            **kwargs,
        )
        self._build_ui()

    def connect_quit(self, callback: Callable[[], None]) -> None:
        self._quit_callbacks.append(callback)

    def _trigger_quit(self) -> None:
        for cb in self._quit_callbacks:
            try:
                cb()
            except Exception:
                pass

    def try_lsd(self) -> None:
        """User chose to explore LSD_OS live session."""
        self._trigger_quit()

    def install_lsd(self) -> None:
        """User chose to install LSD_OS to disk. Launches lsd-calamares in background."""
        try:
            subprocess.Popen(
                ["/usr/bin/lsd-calamares"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            pass
        self._trigger_quit()

    def apply_changes(self) -> None:
        """No config persistence needed on decision step."""
        pass

    def _build_ui(self) -> None:
        # Title & Subtitle
        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
        )
        title_label = Gtk.Label(text="O que você quer fazer agora?")
        title_label.add_css_class("title-1")
        title_box.append(title_label)

        sub_label = Gtk.Label(
            text="Tudo pronto! Você pode explorar o ambiente Live ou instalar definitivamente no seu computador."
        )
        sub_label.add_css_class("dim-label")
        title_box.append(sub_label)
        self.append(title_box)

        # Cards container
        cards_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=24,
            halign=Gtk.Align.CENTER,
        )

        # Try Live Card
        try_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        )
        try_card.set_size_request(290, 240)
        try_card.add_css_class("card")
        try_card.set_margin_top(16)
        try_card.set_margin_bottom(16)
        try_card.set_margin_start(16)
        try_card.set_margin_end(16)

        try_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        try_icon.set_pixel_size(48)
        try_card.append(try_icon)

        try_title = Gtk.Label(text="Experimentar o LSD_OS")
        try_title.add_css_class("heading")
        try_card.append(try_title)

        try_desc = Gtk.Label(
            text="Explore a área de trabalho COSMIC sem alterar seus discos. Suas preferências já estão ativas."
        )
        try_desc.add_css_class("dim-label")
        try_desc.set_justify(Gtk.Justification.CENTER)
        try_desc.set_wrap(True)
        try_card.append(try_desc)

        try_btn = Gtk.Button(label="Experimentar agora")
        try_btn.add_css_class("pill")
        try_btn.connect("clicked", lambda _b: self.try_lsd())
        try_card.append(try_btn)

        cards_box.append(try_card)

        # Install Card
        install_card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        )
        install_card.set_size_request(290, 240)
        install_card.add_css_class("card")
        install_card.set_margin_top(16)
        install_card.set_margin_bottom(16)
        install_card.set_margin_start(16)
        install_card.set_margin_end(16)

        install_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
        install_icon.set_pixel_size(48)
        install_card.append(install_icon)

        install_title = Gtk.Label(text="Instalar no Computador")
        install_title.add_css_class("heading")
        install_card.append(install_title)

        install_desc = Gtk.Label(
            text="Inicie a instalação permanente em disco. O assistente de particionamento abrirá em seguida."
        )
        install_desc.add_css_class("dim-label")
        install_desc.set_justify(Gtk.Justification.CENTER)
        install_desc.set_wrap(True)
        install_card.append(install_desc)

        install_btn = Gtk.Button(label="Instalar o LSD_OS")
        install_btn.add_css_class("suggested-action")
        install_btn.add_css_class("pill")
        install_btn.connect("clicked", lambda _b: self.install_lsd())
        install_card.append(install_btn)

        cards_box.append(install_card)

        self.append(cards_box)
