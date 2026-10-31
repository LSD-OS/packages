#!/usr/bin/env python3
#
# lsdoptional - sincroniza as seleções do netinstall no sistema alvo:
#   1. Remove pacotes pré-instalados na ISO que o usuário desmarcou.
#   2. Habilita serviços dinit correspondentes se Bluetooth ou Impressoras foram instalados.

import libcalamares
from libcalamares.utils import target_env_call


def pretty_name():
    return "Applying package selection"


def _selected_packages():
    """Coleta todos os pacotes que permaneceram marcados no netinstall."""
    selected = set()
    for op in libcalamares.globalstorage.value("packageOperations") or []:
        for key in ("install", "try_install"):
            for item in op.get(key, []) or []:
                if isinstance(item, dict):
                    name = item.get("package") or item.get("name")
                else:
                    name = item
                if name:
                    selected.add(str(name))
    return selected


def _installed(pkg):
    return target_env_call(["pacman", "-Q", pkg]) == 0


def run():
    if not libcalamares.globalstorage.contains("packageOperations"):
        libcalamares.utils.debug("lsdoptional: netinstall não rodou, nada a fazer")
        return None

    selected = _selected_packages()
    preinstalled = libcalamares.job.configuration.get("preinstalled", []) or []

    # 1. Remove pacotes pré-instalados na ISO que foram desmarcados pelo usuário
    to_remove = [p for p in preinstalled if p not in selected and _installed(p)]
    if to_remove:
        libcalamares.utils.debug("lsdoptional: removendo pacotes desmarcados: %s" % to_remove)
        target_env_call(["pacman", "-Rns", "--noconfirm"] + to_remove)

    # 2. Habilita serviços dinit adicionais caso tenham sido instalados
    if _installed("bluez-dinit"):
        target_env_call(["ln", "-sf", "../bluetoothd", "/etc/dinit.d/boot.d/bluetoothd"])

    if _installed("cups-dinit"):
        target_env_call(["ln", "-sf", "../cupsd", "/etc/dinit.d/boot.d/cupsd"])

    return None
