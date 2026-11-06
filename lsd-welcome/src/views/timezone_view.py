"""Step 5: Timezone selection with interactive world map view for LSD-Welcome."""

from __future__ import annotations

from typing import Callable, Any

try:
    from packages.lsd_welcome_pkg import system_config, timezone_picker
    from packages.lsd_welcome_pkg.timezone_picker import TimezonePickerWidget, TimezoneManager
except ImportError:
    try:
        from .. import system_config, timezone_picker  # type: ignore
        from ..timezone_picker import TimezonePickerWidget, TimezoneManager  # type: ignore
    except Exception:
        import system_config  # type: ignore
        import timezone_picker  # type: ignore
        from timezone_picker import TimezonePickerWidget, TimezoneManager  # type: ignore

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = object  # type: ignore


class TimezoneView(Gtk.Box):  # type: ignore
    """Step 5: Interactive Timezone map and city search page."""

    def __init__(
        self,
        tz_manager: TimezoneManager | None = None,
        initial_timezone: str = "America/Sao_Paulo",
        headless: bool = False,
        **kwargs: Any,
    ) -> None:
        self._headless = headless or not GTK_AVAILABLE
        self._selected_timezone = initial_timezone
        self._callbacks: list[Callable[[str], None]] = []

        self.picker_widget = TimezonePickerWidget(
            tz_manager=tz_manager,
            initial_timezone=initial_timezone,
            headless=self._headless,
        )

        def _on_widget_tz_changed(tz: str) -> None:
            self._selected_timezone = tz
            for cb in self._callbacks:
                try:
                    cb(tz)
                except Exception:
                    pass

        self.picker_widget.connect_timezone_changed(_on_widget_tz_changed)

        if self._headless:
            return

        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=14,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            **kwargs,
        )
        self._build_ui()

    def get_selected_timezone(self) -> str:
        return self._selected_timezone

    def set_selected_timezone(self, tz_name: str) -> None:
        self._selected_timezone = tz_name
        self.picker_widget.set_selected_timezone(tz_name)
        for cb in self._callbacks:
            try:
                cb(tz_name)
            except Exception:
                pass

    def connect_timezone_changed(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def apply_changes(self) -> None:
        system_config.apply_timezone(self._selected_timezone)

    def _build_ui(self) -> None:
        # Title & Subtitle
        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            halign=Gtk.Align.CENTER,
        )
        title_label = Gtk.Label(text="Fuso Horário & Localização")
        title_label.add_css_class("title-1")
        title_box.append(title_label)

        sub_label = Gtk.Label(
            text="Selecione sua cidade no mapa mundi ou digite o nome no campo de busca."
        )
        sub_label.add_css_class("dim-label")
        title_box.append(sub_label)
        self.append(title_box)

        # Append interactive TimezonePickerWidget
        self.append(self.picker_widget)
