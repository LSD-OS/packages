#!/bin/bash
set -e

echo "==> Instalando Limine Bootloader (UEFI)..."

ROOT_UUID=$(findmnt -n -o UUID / 2>/dev/null || blkid -s UUID -o value $(findmnt -n -o SOURCE / 2>/dev/null) || true)

if [ -d "/boot/efi/EFI" ] || [ -d "/boot/efi" ]; then
    ESP_DIR="/boot/efi"
elif [ -d "/boot/EFI" ]; then
    ESP_DIR="/boot"
else
    ESP_DIR="/boot/efi"
    mkdir -p "$ESP_DIR"
fi

echo "==> Ponto de montagem da particao ESP: $ESP_DIR"
mkdir -p "$ESP_DIR/EFI/BOOT" "$ESP_DIR/EFI/LSD_OS"

cp -fv /usr/share/limine/BOOTX64.EFI "$ESP_DIR/EFI/BOOT/BOOTX64.EFI" 2>/dev/null || true
cp -fv /usr/share/limine/BOOTIA32.EFI "$ESP_DIR/EFI/BOOT/BOOTIA32.EFI" 2>/dev/null || true
cp -fv /usr/share/limine/BOOTX64.EFI "$ESP_DIR/EFI/LSD_OS/BOOTX64.EFI" 2>/dev/null || true

cat << CONF > "$ESP_DIR/limine.conf"
timeout: 5
interface_branding: LSD_OS!
term_font_scale: 1x1

/LSD_OS Linux
    protocol: linux
    kernel_path: boot():/vmlinuz-linux
    module_path: boot():/initramfs-linux.img
    kernel_cmdline: root=UUID=${ROOT_UUID} rw quiet splash

/LSD_OS Linux (Fallback)
    protocol: linux
    kernel_path: boot():/vmlinuz-linux
    module_path: boot():/initramfs-linux-fallback.img
    kernel_cmdline: root=UUID=${ROOT_UUID} rw
CONF

if [ "$ESP_DIR" != "/boot" ]; then
    cat << CONF > "/boot/limine.conf"
timeout: 5
interface_branding: LSD_OS!
term_font_scale: 1x1

/LSD_OS Linux
    protocol: linux
    kernel_path: boot():/boot/vmlinuz-linux
    module_path: boot():/boot/initramfs-linux.img
    kernel_cmdline: root=UUID=${ROOT_UUID} rw quiet splash

/LSD_OS Linux (Fallback)
    protocol: linux
    kernel_path: boot():/boot/vmlinuz-linux
    module_path: boot():/boot/initramfs-linux-fallback.img
    kernel_cmdline: root=UUID=${ROOT_UUID} rw
CONF
fi

if command -v efibootmgr >/dev/null 2>&1; then
    ESP_DEV=$(findmnt -n -o SOURCE "$ESP_DIR" 2>/dev/null || true)
    if [ -n "$ESP_DEV" ]; then
        DISK="/dev/$(lsblk -no PKNAME "$ESP_DEV" 2>/dev/null || true)"
        PARTNUM=$(lsblk -no PARTN "$ESP_DEV" 2>/dev/null || true)
        if [ -b "$DISK" ] && [ -n "$PARTNUM" ]; then
            echo "==> Registrando entrada UEFI no NVRAM ($DISK p$PARTNUM)..."
            efibootmgr -c -d "$DISK" -p "$PARTNUM" -L "LSD_OS (Limine)" -l "\\EFI\\LSD_OS\\BOOTX64.EFI" 2>/dev/null || true
        fi
    fi
fi

echo "==> Limine UEFI instalado com sucesso!"
