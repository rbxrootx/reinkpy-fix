import argparse
import json
import logging

from . import Device
from .epson import Epson
from .netscan import find as scan_network


_log = logging.getLogger(__name__)


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m reinkpy.main",
        description="Scan Epson network printers and reset supported waste counters.",
    )
    parser.add_argument("--scan", action="store_true", help="Scan the local network for printers.")
    parser.add_argument("--ip", help="Printer IPv4 address.")
    parser.add_argument(
        "--model",
        help="Force a printer model profile when autodetection is wrong or incomplete.",
    )
    parser.add_argument(
        "--read-user",
        default="public",
        help='SNMP read community string. Default: "public".',
    )
    parser.add_argument(
        "--write-user",
        default="private",
        help='SNMP write community string. Default: "private".',
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print all known Epson model profiles and exit.",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print printer information and detected model before exiting.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the waste counter on the selected printer.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print scan or info output as JSON.",
    )
    return parser


def _scan(timeout=4):
    devices = []
    for ip, service_name in scan_network(timeout=timeout):
        if ":" in ip:
            continue
        devices.append(
            {
                "ip": ip,
                "name": service_name,
                "model": None,
                "serial_number": None,
            }
        )
    return devices


def _configure_driver(ip, model, read_user, write_user):
    printer = Device.from_ip(ip, read_user=read_user, write_user=write_user)
    driver = printer.epson
    driver.configure(model or True)
    return printer, driver


def _print(payload, as_json=False):
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        for item in payload:
            print(f"{item['name']} @ {item['ip']}")
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
        return
    print(payload)


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_models:
        for model in sorted(Epson.list_models()):
            print(model)
        return 0

    if args.scan:
        _print(_scan(), as_json=args.json)
        return 0

    if not args.ip:
        parser.error("--ip is required unless --scan or --list-models is used.")

    printer, driver = _configure_driver(
        args.ip,
        args.model,
        args.read_user,
        args.write_user,
    )

    if not driver.spec.model:
        raise SystemExit(
            "Model autodetection failed. Re-run with --model <printer model>."
        )

    info = {
        "ip": printer.ip,
        "name": printer.name,
        "detected_model": driver.detected_model,
        "configured_model": driver.spec.model,
        "serial_number": printer.serial_number,
    }

    if args.info or not args.reset:
        _print(info, as_json=args.json)
        if not args.reset:
            return 0

    _log.info("Resetting waste counter on %s at %s", printer.name, printer.ip)
    if not driver.reset_waste():
        raise SystemExit(
            "The printer did not confirm the reset. Check the model and SNMP settings."
        )
    print("Reset completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
