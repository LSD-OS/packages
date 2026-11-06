"""Step 2: COSMIC Theme selection view (Dark vs Light) for LSD-Welcome."""

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


class ThemeView(Gtk.Box):  # type: ignore
    """Step 2: COSMIC Desktop Theme selection page."""

    def __init__(self, headless: bool = False, **kwargs: Any) -> None:
        self._headless = headless or not GTK_AVAILABLE
        self._selected_theme = "dark"
        self._callbacks: list[Callable[[str], None]] = []

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

    def get_selected_theme(self) -> str:
        return self._selected_theme

    def set_selected_theme(self, mode: str) -> None:
        normalized = mode.strip().lower()
        if normalized not in ("dark", "light"):
            normalized = "dark"
        self._selected_theme = normalized
        self._update_cards_ui()

        for cb in self._callbacks:
            try:
                cb(self._selected_theme)
            except Exception:
                pass

    def connect_theme_changed(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def apply_changes(self) -> None:
        system_config.apply_cosmic_theme(self._selected_theme)

    def _build_ui(self) -> None:
        # Title & Subtitle
        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
        )
        title_label = Gtk.Label(text="Aparência do COSMIC")
        title_label.add_css_class("title-1")
        title_box.append(title_label)

        sub_label = Gtk.Label(
            text="Personalize a aparência do seu sistema. Você pode alterar isso depois a qualquer momento."
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

        # Dark theme card
        self.dark_button = self._create_theme_card(
            theme_id="dark",
            title="Tema Escuro (Padrão)",
            description="Tons profundos elegantes inspirados no COSMIC.\nConfortável para uso prolongado.",
            icon_name="weather-clear-night-symbolic",
        )
        cards_box.append(self.dark_button)

        # Light theme card
        self.light_button = self._create_theme_card(
            theme_id="light",
            title="Tema Claro",
            description="Alta legibilidade e contraste sob luz natural.\nVisual limpo e brilhante.",
            icon_name="weather-clear-symbolic",
        )
        cards_box.append(self.light_button)

        self.append(cards_box)
        self._update_cards_ui()

    def _create_theme_card(
        self,
        theme_id: str,
        title: str,
        description: str,
        icon_name: str,
    ) -> Any:
        btn = Gtk.Button()
        btn.set_size_request(280, 200)
        btn.add_css_class("card")
        btn.add_css_class("theme-card")

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
        )
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(48)
        content.append(icon)

        t_lbl = Gtk.Label(text=title)
        t_lbl.add_css_class("heading")
        content.append(t_lbl)

        d_lbl = Gtk.Label(text=description)
        d_lbl.add_css_class("dim-label")
        d_lbl.set_justify(Gtk.Justification.CENTER)
        d_lbl.set_wrap(True)
        content.append(d_lbl)

        btn.set_child(content)
        btn.connect("clicked", lambda _b: self.set_selected_theme(theme_id))
        return btn

    def _update_cards_ui(self) -> None:
        if self._headless:
            return
        if hasattr(self, "dark_button") and hasattr(self, "light_button"):
            if self._selected_theme == "dark":
                self.dark_button.add_css_class("suggested-action")
                self.dark_button.add_css_class("theme-card-active")
                self.light_button.remove_css_class("suggested-action")
                self.light_button.remove_css_class("theme-card-active")
            else:
                self.light_button.add_css_class("suggested-action")
                self.light_button.add_css_class("theme-card-active")
                self.dark_button.remove_css_class("suggested-action")
                self.dark_button.remove_css_class("theme-card-active")
