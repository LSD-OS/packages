"""Step 4: Internet connection and install mode selection view for LSD-Welcome."""

from __future__ import annotations

from typing import Callable, Any

try:
    from packages.lsd_welcome_pkg import system_config, network_manager
    from packages.lsd_welcome_pkg.network_manager import NetworkService
except ImportError:
    try:
        from .. import system_config, network_manager  # type: ignore
        from ..network_manager import NetworkService  # type: ignore
    except Exception:
        import system_config  # type: ignore
        import network_manager  # type: ignore
        from network_manager import NetworkService  # type: ignore

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = object  # type: ignore


class NetworkView(Gtk.Box):  # type: ignore
    """Step 4: Network status, Wi-Fi scanner and offline installation mode."""

    def __init__(
        self,
        network_service: NetworkService | None = None,
        headless: bool = False,
        **kwargs: Any,
    ) -> None:
        self._headless = headless or not GTK_AVAILABLE
        self.network_service = network_service or NetworkService()
        self._install_mode = "online"
        self._callbacks: list[Callable[[str], None]] = []

        if self._headless:
            return

        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            **kwargs,
        )
        self._build_ui()

    def get_install_mode(self) -> str:
        return self._install_mode

    def set_install_mode(self, mode: str) -> None:
        normalized = mode.strip().lower()
        if normalized not in ("online", "offline"):
            normalized = "online"
        self._install_mode = normalized

        if not self._headless and hasattr(self, "offline_check"):
            self.offline_check.set_active(self._install_mode == "offline")

        for cb in self._callbacks:
            try:
                cb(self._install_mode)
            except Exception:
                pass

    def connect_install_mode_changed(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def apply_changes(self) -> None:
        system_config.set_install_mode(self._install_mode)

    def refresh_networks(self) -> None:
        if self._headless or not hasattr(self, "wifi_listbox"):
            return
        self._populate_wifi_list()

    def _build_ui(self) -> None:
        # Title & Subtitle
        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            halign=Gtk.Align.CENTER,
        )
        title_label = Gtk.Label(text="Conexão com a Internet")
        title_label.add_css_class("title-1")
        title_box.append(title_label)

        sub_label = Gtk.Label(
            text="Conecte-se à internet para atualizar pacotes ou instale offline usando a mídia local."
        )
        sub_label.add_css_class("dim-label")
        title_box.append(sub_label)
        self.append(title_box)

        # Status & Wi-Fi Card
        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
        )
        card.set_size_request(520, 280)
        card.add_css_class("card")
        card.set_margin_top(8)
        card.set_margin_bottom(8)
        card.set_margin_start(16)
        card.set_margin_end(16)

        # Wired status line
        wired_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        wired_box.set_margin_top(12)
        wired_box.set_margin_start(16)
        wired_box.set_margin_end(16)

        has_wired = self.network_service.has_wired_connection()
        wired_icon = Gtk.Image.new_from_icon_name(
            "network-wired-symbolic" if has_wired else "network-wired-disconnected-symbolic"
        )
        wired_box.append(wired_icon)

        wired_text = "Rede cabeada (Ethernet): Conectada" if has_wired else "Rede cabeada: Desconectada"
        self.wired_label = Gtk.Label(text=wired_text)
        self.wired_label.add_css_class("heading" if has_wired else "dim-label")
        wired_box.append(self.wired_label)

        # Refresh button
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Atualizar redes Wi-Fi")
        refresh_btn.set_halign(Gtk.Align.END)
        refresh_btn.set_hexpand(True)
        refresh_btn.connect("clicked", lambda _b: self.refresh_networks())
        wired_box.append(refresh_btn)

        card.append(wired_box)

        # Wi-Fi Scrolled List
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_margin_start(16)
        scroller.set_margin_end(16)
        scroller.set_margin_bottom(12)

        self.wifi_listbox = Gtk.ListBox()
        self.wifi_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.wifi_listbox.add_css_class("boxed-list")
        scroller.set_child(self.wifi_listbox)
        card.append(scroller)

        self.append(card)
        self._populate_wifi_list()

        # Offline installation toggle
        self.offline_check = Gtk.CheckButton.new_with_label(
            "Continuar sem internet (Instalação 100% Offline)"
        )
        self.offline_check.set_halign(Gtk.Align.CENTER)
        self.offline_check.connect("toggled", self._on_offline_toggled)
        self.append(self.offline_check)

    def _on_offline_toggled(self, button: Any) -> None:
        if button.get_active():
            self.set_install_mode("offline")
        else:
            self.set_install_mode("online")

    def _populate_wifi_list(self) -> None:
        # Clear existing
        while True:
            row = self.wifi_listbox.get_first_child()
            if row is None:
                break
            self.wifi_listbox.remove(row)

        try:
            networks = self.network_service.get_wifi_list()
        except Exception:
            networks = []

        if not networks:
            empty_row = Gtk.ListBoxRow()
            lbl = Gtk.Label(text="Nenhuma rede Wi-Fi encontrada ou placa sem fio ausente.")
            lbl.add_css_class("dim-label")
            lbl.set_margin_top(12)
            lbl.set_margin_bottom(12)
            empty_row.set_child(lbl)
            self.wifi_listbox.append(empty_row)
            return

        for net in networks:
            ssid = net.get("ssid", "Rede Oculta")
            signal = net.get("signal", 0)
            security = net.get("security", "")
            active = net.get("active", False)

            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)

            # Signal icon
            icon_name = "network-wireless-signal-excellent-symbolic" if signal > 70 else (
                "network-wireless-signal-good-symbolic" if signal > 40 else "network-wireless-signal-weak-symbolic"
            )
            icon = Gtk.Image.new_from_icon_name(icon_name)
            hbox.append(icon)

            # SSID
            ssid_lbl = Gtk.Label(text=ssid)
            ssid_lbl.set_halign(Gtk.Align.START)
            ssid_lbl.set_hexpand(True)
            if active:
                ssid_lbl.add_css_class("heading")
            hbox.append(ssid_lbl)

            # Security lock
            if security and security != "--":
                lock_icon = Gtk.Image.new_from_icon_name("channel-secure-symbolic")
                lock_icon.set_tooltip_text(security)
                hbox.append(lock_icon)

            # Connect button or Connected badge
            if active:
                badge = Gtk.Label(text="Conectado")
                badge.add_css_class("success")
                hbox.append(badge)
            else:
                conn_btn = Gtk.Button(label="Conectar")
                conn_btn.add_css_class("flat")
                conn_btn.connect("clicked", lambda _b, s=ssid, sec=security: self._on_connect_clicked(s, sec))
                hbox.append(conn_btn)

            row.set_child(hbox)
            self.wifi_listbox.append(row)

    def _on_connect_clicked(self, ssid: str, security: str) -> None:
        # Prompt password dialog if secured
        is_secured = bool(security and security != "--")
        if not is_secured:
            self.network_service.connect_wifi(ssid, password=None)
            self.set_install_mode("online")
            self.refresh_networks()
            return

        # Simple password prompt entry inside dialog or popover
        dialog = Gtk.Window(title=f"Conectar a {ssid}")
        dialog.set_modal(True)
        dialog.set_default_size(320, 160)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        lbl = Gtk.Label(text=f"Digite a senha para '{ssid}':")
        box.append(lbl)

        pwd_entry = Gtk.PasswordEntry()
        box.append(pwd_entry)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END)
        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect("clicked", lambda _b: dialog.close())
        actions.append(cancel_btn)

        ok_btn = Gtk.Button(label="Conectar")
        ok_btn.add_css_class("suggested-action")

        def _do_connect(_b: Any) -> None:
            password = pwd_entry.get_text()
            self.network_service.connect_wifi(ssid, password=password)
            self.set_install_mode("online")
            dialog.close()
            self.refresh_networks()

        ok_btn.connect("clicked", _do_connect)
        actions.append(ok_btn)
        box.append(actions)

        dialog.set_child(box)
        dialog.present()
