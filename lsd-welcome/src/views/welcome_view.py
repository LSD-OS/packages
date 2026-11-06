"""Step 1: Welcome & Language selection view for LSD-Welcome."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Any

try:
    from packages.lsd_welcome_pkg import system_config
except ImportError:
    try:
        from .. import system_config  # type: ignore
    except Exception:
        import system_config  # type: ignore

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GdkPixbuf
    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = object  # type: ignore


SUPPORTED_LANGUAGES = [
    {"label": "Português (Brasil)", "locale": "pt_BR.UTF-8"},
    {"label": "English (US)", "locale": "en_US.UTF-8"},
    {"label": "Español", "locale": "es_ES.UTF-8"},
    {"label": "Français", "locale": "fr_FR.UTF-8"},
    {"label": "Deutsch", "locale": "de_DE.UTF-8"},
    {"label": "Italiano", "locale": "it_IT.UTF-8"},
]


def get_logo_asset_path() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png",
        Path("/usr/share/lsd-welcome/assets/logo.png"),
        Path(__file__).resolve().parents[3] / "mockups" / "logo.png",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


class WelcomeView(Gtk.Box):  # type: ignore
    """Step 1: Welcome and Language selection page."""

    def __init__(self, headless: bool = False, **kwargs: Any) -> None:
        self._headless = headless or not GTK_AVAILABLE
        self._selected_language = "pt_BR.UTF-8"
        self._callbacks: list[Callable[[str], None]] = []

        # Detect system language if pt_BR or en
        env_lang = os.environ.get("LANG", "")
        if "en" in env_lang:
            self._selected_language = "en_US.UTF-8"
        elif "es" in env_lang:
            self._selected_language = "es_ES.UTF-8"

        if self._headless:
            return

        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            **kwargs,
        )
        self._build_ui()

    def get_selected_language(self) -> str:
        return self._selected_language

    def set_selected_language(self, locale_str: str) -> None:
        self._selected_language = locale_str
        for cb in self._callbacks:
            try:
                cb(locale_str)
            except Exception:
                pass

    def connect_language_changed(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def apply_changes(self) -> None:
        system_config.apply_language(self._selected_language)

    def _build_ui(self) -> None:
        # Logo
        logo_path = get_logo_asset_path()
        if logo_path and logo_path.exists():
            logo_img = Gtk.Image.new_from_file(str(logo_path))
            logo_img.set_pixel_size(128)
            logo_img.add_css_class("welcome-logo")
            self.append(logo_img)

        # Title
        title_label = Gtk.Label(text="Bem-vindo ao LSD_OS")
        title_label.add_css_class("title-1")
        title_label.add_css_class("welcome-title")
        self.append(title_label)

        # Subtitle
        sub_label = Gtk.Label(
            text="Selecione o idioma de sua preferência para configurar o sistema:"
        )
        sub_label.add_css_class("body")
        sub_label.add_css_class("dim-label")
        self.append(sub_label)

        # Dropdown container
        combo_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
            halign=Gtk.Align.CENTER,
        )

        labels = [item["label"] for item in SUPPORTED_LANGUAGES]
        string_list = Gtk.StringList.new(labels)
        self.dropdown = Gtk.DropDown.new(string_list, None)
        self.dropdown.set_size_request(260, 42)

        # Set default index
        selected_idx = 0
        for i, item in enumerate(SUPPORTED_LANGUAGES):
            if item["locale"] == self._selected_language:
                selected_idx = i
                break
        self.dropdown.set_selected(selected_idx)
        self.dropdown.connect("notify::selected", self._on_dropdown_changed)

        combo_box.append(self.dropdown)
        self.append(combo_box)

    def _on_dropdown_changed(self, dropdown: Any, _param: Any) -> None:
        idx = dropdown.get_selected()
        if 0 <= idx < len(SUPPORTED_LANGUAGES):
            self.set_selected_language(SUPPORTED_LANGUAGES[idx]["locale"])
