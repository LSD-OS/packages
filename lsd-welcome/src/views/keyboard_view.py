"""Step 3: Keyboard layout selection and typing test view for LSD-Welcome."""

from __future__ import annotations

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
    from gi.repository import Gtk
    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = object  # type: ignore


SUPPORTED_KEYBOARDS = [
    {
        "label": "Português (Brasil) - ABNT2 (Padrão)",
        "layout": "br",
        "variant": "abnt2",
        "vconsole": "br-abnt2",
    },
    {
        "label": "Português (Brasil) - Internacional / Thinkpad",
        "layout": "br",
        "variant": "thinkpad",
        "vconsole": "br-abnt2",
    },
    {
        "label": "Inglês (EUA) - Internacional com teclas mortas (AltGr)",
        "layout": "us",
        "variant": "altgr-intl",
        "vconsole": "us",
    },
    {
        "label": "Inglês (EUA) - Padrão",
        "layout": "us",
        "variant": "",
        "vconsole": "us",
    },
    {
        "label": "Espanhol - Padrão",
        "layout": "es",
        "variant": "",
        "vconsole": "es",
    },
    {
        "label": "Francês - AZERTY",
        "layout": "fr",
        "variant": "",
        "vconsole": "fr",
    },
    {
        "label": "Alemão - QWERTZ",
        "layout": "de",
        "variant": "",
        "vconsole": "de-latin1",
    },
]


class KeyboardView(Gtk.Box):  # type: ignore
    """Step 3: Keyboard layout selection and interactive test page."""

    def __init__(self, headless: bool = False, **kwargs: Any) -> None:
        self._headless = headless or not GTK_AVAILABLE
        self._layout = "br"
        self._variant = "abnt2"
        self._vconsole = "br-abnt2"
        self._callbacks: list[Callable[[dict], None]] = []

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

    def get_selected_keyboard(self) -> dict[str, str]:
        return {
            "layout": self._layout,
            "variant": self._variant,
            "vconsole": self._vconsole,
        }

    def set_selected_keyboard(
        self,
        layout: str,
        variant: str = "",
        vconsole: str = "",
    ) -> None:
        self._layout = layout
        self._variant = variant
        self._vconsole = vconsole or layout

        # Update dropdown if UI active
        if not self._headless and hasattr(self, "dropdown"):
            for i, item in enumerate(SUPPORTED_KEYBOARDS):
                if item["layout"] == layout and item["variant"] == variant:
                    self.dropdown.set_selected(i)
                    break

        for cb in self._callbacks:
            try:
                cb(self.get_selected_keyboard())
            except Exception:
                pass

    def connect_keyboard_changed(self, callback: Callable[[dict], None]) -> None:
        self._callbacks.append(callback)

    def apply_changes(self) -> None:
        system_config.apply_keyboard(self._layout, self._variant, self._vconsole)

    def _build_ui(self) -> None:
        # Title & Subtitle
        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
        )
        title_label = Gtk.Label(text="Disposição do Teclado")
        title_label.add_css_class("title-1")
        title_box.append(title_label)

        sub_label = Gtk.Label(
            text="Escolha a disposição correta e teste a digitação com acentos abaixo."
        )
        sub_label.add_css_class("dim-label")
        title_box.append(sub_label)
        self.append(title_box)

        # Dropdown container
        selector_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
        )

        labels = [item["label"] for item in SUPPORTED_KEYBOARDS]
        string_list = Gtk.StringList.new(labels)
        self.dropdown = Gtk.DropDown.new(string_list, None)
        self.dropdown.set_size_request(420, 42)
        self.dropdown.set_selected(0)
        self.dropdown.connect("notify::selected", self._on_dropdown_changed)
        selector_box.append(self.dropdown)
        self.append(selector_box)

        # Test field container
        test_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
        )
        test_label = Gtk.Label(text="Teste de digitação:")
        test_label.add_css_class("heading")
        test_label.set_halign(Gtk.Align.START)
        test_box.append(test_label)

        self.test_entry = Gtk.Entry()
        self.test_entry.set_placeholder_text("Digite aqui para testar: ç, á, õ, ê, à, ~, ^...")
        self.test_entry.set_size_request(420, 42)
        test_box.append(self.test_entry)
        self.append(test_box)

    def _on_dropdown_changed(self, dropdown: Any, _param: Any) -> None:
        idx = dropdown.get_selected()
        if 0 <= idx < len(SUPPORTED_KEYBOARDS):
            item = SUPPORTED_KEYBOARDS[idx]
            self.set_selected_keyboard(item["layout"], item["variant"], item["vconsole"])
            # Apply immediately in live session so test entry tests the chosen layout
            self.apply_changes()
