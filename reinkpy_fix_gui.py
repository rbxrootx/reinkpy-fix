import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import reinkpy
from reinkpy.epson import Epson
from reinkpy.netscan import find as scan_network


APP_NAME = "ReInkPy Fix"
AUTODETECT_MODEL = "Autodetect"


class QueueLogHandler(logging.Handler):
    def __init__(self, output_queue):
        super().__init__()
        self.output_queue = output_queue

    def emit(self, record):
        self.output_queue.put(self.format(record))


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x560")
        self.root.minsize(700, 500)

        self.log_queue = queue.Queue()
        self.devices = {}
        self.busy = False

        self.selected_device_var = tk.StringVar()
        self.ip_var = tk.StringVar()
        self.read_user_var = tk.StringVar(value="public")
        self.write_user_var = tk.StringVar(value="private")
        self.model_var = tk.StringVar(value=AUTODETECT_MODEL)
        self.detected_var = tk.StringVar(value="Not connected")
        self.status_var = tk.StringVar(
            value="LAN only. Scan or enter the printer IP address, then click Connect."
        )

        self._configure_logging()
        self._build_ui()
        self.root.after(100, self._flush_logs)

    def _configure_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root_logger.addHandler(handler)
        self.log_handler = handler

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.rowconfigure(8, weight=1)

        ttk.Label(
            frame,
            text="Waste ink counter reset for supported Epson network printers.",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            frame,
            text=(
                "This does not repair hardware. It only sends the reset command. "
                "Use it only after servicing the waste ink pads/tank."
            ),
            wraplength=700,
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 12))

        ttk.Label(frame, text="Discovered printers").grid(row=2, column=0, sticky="w")
        self.device_combo = ttk.Combobox(
            frame,
            textvariable=self.selected_device_var,
            state="readonly",
            values=[],
        )
        self.device_combo.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(0, 8))
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)
        self.scan_button = ttk.Button(frame, text="Scan", command=self.scan)
        self.scan_button.grid(row=2, column=3, sticky="ew")

        ttk.Label(frame, text="Printer IP").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.ip_var).grid(
            row=3, column=1, columnspan=3, sticky="ew", pady=(8, 0)
        )

        ttk.Label(frame, text="Model").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.model_combo = ttk.Combobox(
            frame,
            textvariable=self.model_var,
            values=[AUTODETECT_MODEL, *sorted(Epson.list_models())],
        )
        self.model_combo.grid(row=4, column=1, columnspan=3, sticky="ew", pady=(8, 0))

        ttk.Label(frame, text="SNMP read").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.read_user_var).grid(
            row=5, column=1, sticky="ew", pady=(8, 0), padx=(0, 8)
        )
        ttk.Label(frame, text="SNMP write").grid(row=5, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.write_user_var).grid(
            row=5, column=3, sticky="ew", pady=(8, 0)
        )

        ttk.Label(frame, text="Detected printer").grid(row=6, column=0, sticky="w", pady=(8, 0))
        ttk.Label(frame, textvariable=self.detected_var).grid(
            row=6, column=1, columnspan=3, sticky="w", pady=(8, 0)
        )

        button_bar = ttk.Frame(frame)
        button_bar.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(16, 8))
        button_bar.columnconfigure((0, 1), weight=1)
        self.connect_button = ttk.Button(button_bar, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.reset_button = ttk.Button(button_bar, text="Reset Waste Counter", command=self.reset)
        self.reset_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(frame, textvariable=self.status_var, wraplength=700).grid(
            row=8, column=0, columnspan=4, sticky="new"
        )

        self.log_output = ScrolledText(frame, height=14, wrap="word", state="disabled")
        self.log_output.grid(row=9, column=0, columnspan=4, sticky="nsew", pady=(8, 0))

    def _set_busy(self, busy, status=None):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.scan_button.configure(state=state)
        self.connect_button.configure(state=state)
        self.reset_button.configure(state=state)
        if status is not None:
            self.status_var.set(status)

    def _flush_logs(self):
        changed = False
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            changed = True
            self.log_output.configure(state="normal")
            self.log_output.insert("end", message + "\n")
            self.log_output.see("end")
            self.log_output.configure(state="disabled")
        if changed:
            self.root.update_idletasks()
        self.root.after(100, self._flush_logs)

    def _on_device_selected(self, _event=None):
        device = self.devices.get(self.selected_device_var.get())
        if not device:
            return
        self.ip_var.set(device["ip"])
        if device.get("model"):
            self.model_var.set(device["model"])
        self.detected_var.set(device["description"])

    def _build_device(self, ip=None):
        printer_ip = (ip or self.ip_var.get()).strip()
        if not printer_ip:
            raise ValueError("Enter the printer IP address first.")
        return reinkpy.Device.from_ip(
            printer_ip,
            read_user=(self.read_user_var.get().strip() or "public"),
            write_user=(self.write_user_var.get().strip() or "private"),
        )

    def _resolve_driver(self):
        printer = self._build_device()
        driver = printer.epson
        selected_model = self.model_var.get().strip()
        if selected_model and selected_model != AUTODETECT_MODEL:
            driver.configure(selected_model)
        else:
            driver.configure(True)
        if not driver.spec.model:
            raise RuntimeError(
                "Model autodetection failed. Pick the printer model manually and try again."
            )
        return printer, driver

    def _run_task(self, work, on_done):
        def runner():
            try:
                result = work()
            except Exception as exc:
                logging.exception(str(exc))
                self.root.after(0, lambda: on_done(exc, None))
            else:
                self.root.after(0, lambda: on_done(None, result))

        threading.Thread(target=runner, daemon=True).start()

    def scan(self):
        if self.busy:
            return

        def work():
            results = []
            logging.info("Scanning local network for printers...")
            for ip, service_name in scan_network(timeout=4):
                if ":" in ip:
                    continue
                description = f"{service_name} ({ip})"
                model = ""
                try:
                    device = self._build_device(ip=ip)
                    model = device.epson.detected_model or ""
                    if model:
                        description = f"{service_name} ({ip}) [{model}]"
                except Exception:
                    logging.warning("Found %s but could not read model details yet.", description)
                results.append(
                    {
                        "label": description,
                        "description": description,
                        "ip": ip,
                        "model": model,
                    }
                )
            return results

        def done(error, results):
            self._set_busy(False)
            if error:
                self.status_var.set(str(error))
                return
            self.devices = {item["label"]: item for item in results}
            self.device_combo.configure(values=list(self.devices))
            if results:
                first = results[0]["label"]
                self.selected_device_var.set(first)
                self._on_device_selected()
                self.status_var.set("Select a printer and click Connect.")
                logging.info("Scan complete. Found %d printer(s).", len(results))
            else:
                self.selected_device_var.set("")
                self.detected_var.set("No printers discovered")
                self.status_var.set("No printers were found. Enter the printer IP manually.")
                logging.warning("No printers found on the local network.")

        self._set_busy(True, "Scanning for Epson printers...")
        self._run_task(work, done)

    def connect(self):
        if self.busy:
            return

        def work():
            printer, driver = self._resolve_driver()
            info = printer.info
            return {
                "ip": printer.ip,
                "model": driver.spec.model,
                "serial": info.get("SN") or info.get("serial_number") or "Unknown",
                "name": printer.name,
            }

        def done(error, result):
            self._set_busy(False)
            if error:
                self.status_var.set(str(error))
                return
            self.detected_var.set(
                f"{result['name']} | Model profile: {result['model']} | Serial: {result['serial']}"
            )
            self.status_var.set("Connected. You can reset the waste counter now.")
            logging.info("Connected to %s at %s.", result["name"], result["ip"])

        self._set_busy(True, "Connecting to the printer...")
        self._run_task(work, done)

    def reset(self):
        if self.busy:
            return
        if not messagebox.askyesno(
            APP_NAME,
            (
                "Send the waste counter reset command now?\n\n"
                "Make sure the printer is powered on and connected to the same network."
            ),
        ):
            return

        def work():
            printer, driver = self._resolve_driver()
            logging.info("Sending reset command to %s at %s...", printer.name, printer.ip)
            result = driver.reset_waste()
            if not result:
                raise RuntimeError(
                    "The printer did not confirm the reset. Check the model and SNMP settings."
                )
            return printer

        def done(error, printer):
            self._set_busy(False)
            if error:
                self.status_var.set(str(error))
                return
            self.status_var.set("Reset completed. Power-cycle the printer if it still shows the error.")
            self.detected_var.set(f"{printer.name} at {printer.ip}")
            logging.info("Reset completed successfully.")
            messagebox.showinfo(
                APP_NAME,
                "Reset completed. If the printer still reports the waste ink error, turn it off and back on.",
            )

        self._set_busy(True, "Resetting the waste counter...")
        self._run_task(work, done)


def main():
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
