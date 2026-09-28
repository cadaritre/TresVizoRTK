"""Banco BLE del Meridian V. Uso: `python3 tools/ble_bench <orden> …` (ver --help).

Sin radio (biblioteca estándar): decode, rtcm-generate, rtcm-check, replay, list,
y `run … --sim` contra el simulador. Con radio: `run …` necesita bleak (ver
bench/ble_link.py para instalarlo).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from bench import protocol as p  # noqa: E402
from bench import rtcm  # noqa: E402
from bench.analysis import analyze_events  # noqa: E402
from bench.session import Recorder, read_session  # noqa: E402

DEFAULT_SESSIONS_DIR = HERE / "sesiones-banco"


def _plain(value):
    if is_dataclass(value):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, bytes):
        return value.hex()
    return value


def cmd_decode(args) -> int:
    if args.solution:
        print(json.dumps(_plain(p.decode_solution(bytes.fromhex(args.solution))), ensure_ascii=False, indent=2))
    if args.health:
        packet = p.decode_health(bytes.fromhex(args.health))
        out = _plain(packet)
        out["correction_source_name"] = packet.correction_source_name
        out["bytes_1_to_4_are_display_precision"] = packet.bytes_1_to_4_are_display_precision
        print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.response:
        reassembler = p.ResponseReassembler(negotiated_mtu=args.mtu)
        for index, frame in enumerate(args.response):
            for outcome in reassembler.feed(bytes.fromhex(frame), float(index)):
                text = outcome.message.decode("utf-8", "replace") if outcome.message else ""
                print(f"trama {index}: {outcome.kind} id={outcome.message_id} {outcome.detail} {text}".rstrip())
    if args.rtcm:
        parser = rtcm.Rtcm3Parser()
        for frame in parser.feed(bytes.fromhex(args.rtcm)):
            print(f"RTCM {rtcm.message_number(frame)}: {len(frame)} B")
        print(f"aceptadas {parser.accepted}, CRC malos {parser.rejected}, bytes sin cerrar {parser.buffered_bytes}")
    return 0


def cmd_rtcm_generate(args) -> int:
    profile = rtcm.EpochProfile(msm_kind=args.msm, inert_message_number=4095 if args.inert else None)
    generator = rtcm.RtcmGenerator(profile, seed=args.seed)
    with open(args.out, "wb") as handle:
        for epoch in range(args.epochs):
            for item in generator.epoch(epoch, epoch * 1000):
                handle.write(item.frame)
    print(f"{args.out}: {generator.frames_generated} tramas, {generator.bytes_generated} B "
          f"({generator.bytes_generated / max(args.epochs, 1):.0f} B por época de 1 s)")
    return 0


def cmd_rtcm_check(args) -> int:
    paths = [Path(x) for x in args.files] or rtcm.find_capture_files(HERE.parents[1])
    if not paths:
        print("no hay capturas RTCM en captures/, data/ ni tests/ del repositorio")
        return 1
    for path in paths:
        frames, parser = rtcm.read_frames_from_file(path)
        by_number: dict[int, list[int]] = {}
        for frame in frames:
            by_number.setdefault(rtcm.message_number(frame), []).append(len(frame))
        size = path.stat().st_size
        framed = sum(len(f) for f in frames)
        print(f"{path}: {size} B, {parser.accepted} tramas válidas ({framed} B), {parser.rejected} con CRC malo, "
              f"{size - framed} B fuera de trama")
        for number, sizes in sorted(by_number.items()):
            print(f"  {number}: {len(sizes)} tramas, {min(sizes)}–{max(sizes)} B")
    return 0


def cmd_replay(args) -> int:
    header, events = read_session(Path(args.session))
    analyzer = analyze_events(events)
    print(f"sesión grabada el {header.get('started_utc')} ({header.get('metadata', {}).get('scenario', '?')})")
    print(analyzer.render("Reproducción"))
    return 0


def cmd_list(_args) -> int:
    from bench.scenarios import SCENARIOS
    for name, scenario in SCENARIOS.items():
        print(f"{name:14} {scenario.description}  {scenario.defaults}")
    return 0


def cmd_run(args) -> int:
    from bench.runner import Bench
    from bench.scenarios import SCENARIOS, ScenarioOptions
    scenario = SCENARIOS[args.scenario]
    options = ScenarioOptions(**scenario.defaults)
    for field, value in (("duration_s", args.duration), ("rate_bytes_per_second", args.rate),
                         ("command_period_s", args.command_period), ("cycles", args.cycles),
                         ("burst_seconds", args.burst), ("msm_kind", args.msm), ("seed", args.seed)):
        if value is not None:
            setattr(options, field, value)
    options.select_ble_source = args.select_ble_source
    options.inert = args.inert
    options.rtcm_file = Path(args.rtcm_file) if args.rtcm_file else None

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else DEFAULT_SESSIONS_DIR / f"{stamp}-{args.scenario}"
    out.mkdir(parents=True, exist_ok=True)
    if args.sim:
        from bench.simulator import SimulatedLink, SimulatedMeridian, SimulatorOptions
        device = SimulatedMeridian(SimulatorOptions(receiver_talking=not args.sim_silent_receiver,
                                                    write_without_response=not args.sim_no_wwr))
        link_factory = lambda: SimulatedLink(device)  # noqa: E731
        link_kind = "simulador"
    else:
        from bench.ble_link import BleakLink, _bleak
        from bench.link import LinkError
        try:
            _bleak()
        except LinkError as error:
            print(error, file=sys.stderr)
            return 2
        link_factory = lambda: BleakLink(address=args.address, name=args.name)  # noqa: E731
        link_kind = "bluetooth"
    metadata = {"scenario": args.scenario, "link": link_kind, "options": _plain(options)}
    metadata["options"]["rtcm_file"] = str(options.rtcm_file) if options.rtcm_file else None
    recorder = Recorder(out / "sesion.jsonl", out / "eventos.csv", metadata=metadata)
    bench = Bench(link_factory, recorder, allow_mutations=args.select_ble_source)
    print(f"escenario {args.scenario}: {scenario.description}\nregistro en {out}", flush=True)
    code = 0
    try:
        asyncio.run(scenario.run(bench, options))
    except KeyboardInterrupt:
        bench.note("interrumpido por el operador")
        code = 130
    except Exception as error:
        recorder.record("note", text=f"el escenario terminó con error: {type(error).__name__}: {error}")
        print(f"el escenario terminó con error: {type(error).__name__}: {error}", file=sys.stderr)
        code = 1
    finally:
        recorder.close()
    summary = bench.analyzer.render(f"Escenario {args.scenario} ({link_kind})")
    (out / "resumen.txt").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ble_bench", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    decode = sub.add_parser("decode", help="decodificar paquetes en hexadecimal")
    decode.add_argument("--solution", help="paquete de solución (20 bytes)")
    decode.add_argument("--health", help="paquete de salud (20 bytes)")
    decode.add_argument("--response", nargs="+", help="tramas de respuesta en orden de llegada")
    decode.add_argument("--mtu", type=int, help="MTU negociado, para marcar tramas demasiado largas")
    decode.add_argument("--rtcm", help="flujo RTCM3 en hexadecimal")
    decode.set_defaults(func=cmd_decode)

    generate = sub.add_parser("rtcm-generate", help="escribir un archivo RTCM3 sintético")
    generate.add_argument("out")
    generate.add_argument("--epochs", type=int, default=60, help="épocas de 1 s (defecto 60)")
    generate.add_argument("--msm", type=int, choices=(4, 7), default=7)
    generate.add_argument("--inert", action="store_true", help="número de mensaje 4095 en vez de los reales")
    generate.add_argument("--seed", type=int, default=1)
    generate.set_defaults(func=cmd_rtcm_generate)

    check = sub.add_parser("rtcm-check", help="validar capturas RTCM3 como lo haría el ESP32")
    check.add_argument("files", nargs="*", help="archivos; sin ninguno, busca en captures/, data/ y tests/")
    check.set_defaults(func=cmd_rtcm_check)

    replay = sub.add_parser("replay", help="reproducir una sesión grabada contra el decodificador")
    replay.add_argument("session", help="sesion.jsonl")
    replay.set_defaults(func=cmd_replay)

    listing = sub.add_parser("list", help="escenarios disponibles")
    listing.set_defaults(func=cmd_list)

    from bench.scenarios import SCENARIOS
    run = sub.add_parser("run", help="correr un escenario (Bluetooth, o --sim)")
    run.add_argument("scenario", choices=sorted(SCENARIOS))
    run.add_argument("--sim", action="store_true", help="contra el simulador en proceso, sin radio")
    run.add_argument("--sim-silent-receiver", action="store_true", help="simulador con el UM980 mudo")
    run.add_argument("--sim-no-wwr", action="store_true", help="simulador sin escritura sin respuesta en RTCM")
    run.add_argument("--address", help="dirección (en macOS, el UUID que asigna CoreBluetooth)")
    run.add_argument("--name", help="parte del nombre anunciado, si no se filtra por servicio")
    run.add_argument("--duration", type=float, help="segundos")
    run.add_argument("--rate", type=float, help="RTCM, bytes por segundo")
    run.add_argument("--command-period", type=float, help="segundos entre órdenes periódicas")
    run.add_argument("--cycles", type=int, help="ciclos de reconexión o de corte")
    run.add_argument("--burst", type=float, help="segundos de RTCM por ráfaga")
    run.add_argument("--msm", type=int, choices=(4, 7))
    run.add_argument("--inert", action="store_true", help="RTCM con número 4095 (no alimenta el RTK)")
    run.add_argument("--rtcm-file", help="captura RTCM3 real para repetir en bucle")
    run.add_argument("--seed", type=int)
    run.add_argument("--select-ble-source", action="store_true",
                     help="permite PUT /api/corrections/source {\"source\":\"ble\"} (cambia el estado del equipo)")
    run.add_argument("--out", help="carpeta de salida (defecto tools/ble_bench/sesiones-banco/…)")
    run.set_defaults(func=cmd_run)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
