#!/usr/bin/env python3
"""OSM-Auslieferungseinstellungen anwenden oder pruefen (Nerd*-Fork).

Hintergrund: Unsere Abweichungen vom Upstream (Pool, Worker, Hostname, SSID,
Luefter, Takte) lagen frueher als Diff-Schnipsel im Git-Verlauf. Beim Nachziehen
einer neuen Upstream-Version konnten sie verloren gehen oder nur teilweise
ankommen - daher die veralteten und uneinheitlichen Images.

Jetzt stehen die Werte in osm-settings.json, und dieses Skript schreibt sie an
die drei Stellen, an denen diese Firmware ihre Vorgaben haelt:

  * main/Kconfig.projbuild      - Standardwerte des Projekts
  * sdkconfig.defaults          - uebersteuert Kconfig beim Bauen (falls gesetzt)
  * main/boards/<board>.cpp     - Auslieferungstakt je Geraet

  python3 tools/osm_settings.py --apply    # nach jedem Upstream-Rebase
  python3 tools/osm_settings.py --check    # laeuft in der CI vor jedem Release
"""

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "osm-settings.json"
KCONFIG = ROOT / "main" / "Kconfig.projbuild"
SDKCONFIG = ROOT / "sdkconfig.defaults"
BOARDS = ROOT / "main" / "boards"


def kconfig_targets(g):
    return {
        "STRATUM_URL": f'"{g["pool"]["url"]}"',
        "STRATUM_PORT": str(g["pool"]["port"]),
        "STRATUM_USER": f'"{g["pool"]["user"]}"',
        "STRATUM_PW": f'"{g["pool"]["password"]}"',
        "STRATUM_FALLBACK_URL": f'"{g["backup_pool"]["url"]}"',
        "STRATUM_FALLBACK_PORT": str(g["backup_pool"]["port"]),
        "STRATUM_FALLBACK_USER": f'"{g["backup_pool"]["user"]}"',
        "STRATUM_FALLBACK_PW": f'"{g["backup_pool"]["password"]}"',
        "ESP_WIFI_SSID": f'"{g["wifi_ssid"]}"',
        "OVERHEAT_TEMP": str(g["overheat_temp"]),
    }


def patch_kconfig(cfg, apply_changes):
    g = cfg["general"]
    text = KCONFIG.read_text(encoding="utf-8")
    drift = []

    for name, want in kconfig_targets(g).items():
        pattern = re.compile(
            r"(config %s\b(?:(?!\n\s*config\s).)*?\n\s*default\s+)(\S+)" % re.escape(name), re.S
        )
        m = pattern.search(text)
        if not m:
            drift.append(f"{name}: Eintrag nicht gefunden")
            continue
        if m.group(2) != want:
            drift.append(f"{name}: {m.group(2)} -> {want}")
            text = text[: m.start(2)] + want + text[m.end(2) :]

    # Luefterbetriebsart (choice-Block)
    want_fan = {"pid": "FAN_MODE_PID", "manual": "FAN_MODE_MANUAL"}[g["fan_mode"]]
    m = re.search(r'(prompt "Fan speed control mode"\s*\n\s*default\s+)(\S+)', text)
    if not m:
        drift.append("Fan-Mode: Auswahlblock nicht gefunden")
    elif m.group(2) != want_fan:
        drift.append(f"Fan-Mode: {m.group(2)} -> {want_fan}")
        text = text[: m.start(2)] + want_fan + text[m.end(2) :]

    if drift and apply_changes:
        KCONFIG.write_text(text, encoding="utf-8", newline="\n")
    return drift


def patch_sdkconfig(cfg, apply_changes):
    """sdkconfig.defaults uebersteuert Kconfig - nur bereits vorhandene Zeilen anfassen."""
    if not SDKCONFIG.exists():
        return []
    g = cfg["general"]
    targets = {
        "CONFIG_STRATUM_URL": f'"{g["pool"]["url"]}"',
        "CONFIG_STRATUM_PORT": str(g["pool"]["port"]),
        "CONFIG_STRATUM_USER": f'"{g["pool"]["user"]}"',
        "CONFIG_LWIP_LOCAL_HOSTNAME": f'"{g["hostname"]}"',
        "CONFIG_OVERHEAT_TEMP": str(g["overheat_temp"]),
    }
    lines = SDKCONFIG.read_text(encoding="utf-8").splitlines()
    drift = []

    for i, line in enumerate(lines):
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key not in targets:
            continue
        want = targets[key]
        got = value.split("#")[0].strip()
        if got != want:
            drift.append(f"{key}: {got} -> {want}")
            comment = line[line.index("#"):] if "#" in line else ""
            lines[i] = f"{key}={want}" + (f"   {comment}" if comment else "")

    if drift and apply_changes:
        SDKCONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return drift


def patch_board(name, dev, apply_changes):
    """Auslieferungstakt in main/boards/<name>.cpp."""
    path = BOARDS / f"{name}.cpp"
    if not path.exists():
        return [f"{name}.cpp fehlt - Board umbenannt oder entfernt?"]
    text = path.read_text(encoding="utf-8")
    drift = []

    edits = []
    if "frequency" in dev:
        edits.append((r"(m_defaultAsicFrequency\s*=\s*m_asicFrequency\s*=\s*)(\d+)", str(dev["frequency"]), "Frequenz"))
    if "core_voltage" in dev:
        edits.append((r"(m_defaultAsicVoltageMillis\s*=\s*m_asicVoltageMillis\s*=\s*)(\d+)", str(dev["core_voltage"]), "Kernspannung"))

    for pattern, want, label in edits:
        m = re.search(pattern, text)
        if not m:
            drift.append(f"{label}: Zuweisung nicht gefunden")
            continue
        if m.group(2) != want:
            drift.append(f"{label}: {m.group(2)} -> {want}")
            text = text[: m.start(2)] + want + text[m.end(2) :]

    if drift and apply_changes:
        path.write_text(text, encoding="utf-8", newline="\n")
    return drift


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="Werte in die Firmware-Dateien schreiben")
    mode.add_argument("--check", action="store_true", help="nur pruefen, Abweichung = Exit-Code 1")
    args = ap.parse_args()

    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    total = 0

    for label, drift in [
        (KCONFIG.relative_to(ROOT).as_posix(), patch_kconfig(cfg, args.apply)),
        (SDKCONFIG.relative_to(ROOT).as_posix(), patch_sdkconfig(cfg, args.apply)),
    ]:
        if drift:
            total += len(drift)
            print(f"{label}:")
            for d in drift:
                print(f"    {d}")

    for name, dev in cfg["devices"].items():
        drift = patch_board(name, dev, args.apply)
        if drift:
            total += len(drift)
            print(f"main/boards/{name}.cpp:")
            for d in drift:
                print(f"    {d}")

    if not total:
        print("OSM-Einstellungen: alles wie in osm-settings.json.")
        return 0
    if args.apply:
        print(f"\n{total} Werte angepasst.")
        return 0
    print(f"\n{total} Abweichung(en) von osm-settings.json - 'tools/osm_settings.py --apply' ausfuehren.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
