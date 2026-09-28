// Banco BLE del Meridian V para macOS, con CoreBluetooth (sin instalar nada).
//
// Uso (lo arma `build.sh` como MeridianBench.app, porque macOS exige una app con
// descripción de uso para el Bluetooth):
//   open -W -n MeridianBench.app --args <registro.log> <segundos> <modo> [bytes_por_epoca]
// Modos:
//   burst  — una época RTCM de `bytes_por_epoca` (5000 por defecto) al empezar cada segundo
//            (lo que hace un caster), sin respuesta si el equipo lo anuncia
//   sat    — RTCM tan rápido como lo acepte la pila (saturar el enlace)
//   none   — sin RTCM: solo órdenes y salud
// En los tres, una orden `GET /api/ble` cada 250 ms con su latencia, y la salud con sus
// intervalos. Las tramas son RTCM3 de tipo 4095 (propietario) con CRC-24Q válido: el UM980
// las ignora. No cambia la fuente de correcciones del equipo: con NTRIP activo, el router
// las rechaza por fuente y cuentan en `rtcm_dropped_frames` y en el byte 18 de la salud.
//
// Ojo: si la Mac se conectó antes a un firmware viejo, usa su tabla GATT en caché
// (docs/connectivity/KNOWN_LIMITATIONS.md) y verá la RTCM solo «con respuesta».
import CoreBluetooth
import Foundation
let logURL = URL(fileURLWithPath: CommandLine.arguments[1])
let seconds = Double(CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : "20")!
let mode = CommandLine.arguments.count > 3 ? CommandLine.arguments[3] : "burst"
let epochBytes = Int(CommandLine.arguments.count > 4 ? CommandLine.arguments[4] : "5000")!
FileManager.default.createFile(atPath: logURL.path, contents: nil)
let log = try! FileHandle(forWritingTo: logURL)
func now() -> Double { ProcessInfo.processInfo.systemUptime }
func say(_ s: String) { log.write(String(format: "%.3f %@\n", now(), s).data(using: .utf8)!) }
func uuid(_ p: String) -> CBUUID { CBUUID(string: "\(p)-8f24-4adb-a350-77ef6339c320") }
let svc = uuid("a04c0001"), cmd = uuid("a04c0002"), rsp = uuid("a04c0003"), rtcmU = uuid("a04c0005"), hlt = uuid("a04c0006")
// CRC-24Q de RTCM3.
func crc24q(_ d: [UInt8]) -> UInt32 { var c: UInt32 = 0; for b in d { c ^= UInt32(b) << 16; for _ in 0..<8 { c <<= 1; if c & 0x1000000 != 0 { c ^= 0x1864CFB } } }; return c & 0xFFFFFF }
// Trama de tipo 4095 (propietario; el UM980 la ignora) con `payload` bytes.
func frame(_ payload: Int, _ seq: Int) -> [UInt8] {
    var p = [UInt8](repeating: UInt8(seq & 0xff), count: payload); p[0] = 0xFF; p[1] = 0xF0
    var f: [UInt8] = [0xD3, UInt8((payload >> 8) & 3), UInt8(payload & 0xff)] + p
    let c = crc24q(f); f += [UInt8(c >> 16), UInt8((c >> 8) & 0xff), UInt8(c & 0xff)]; return f
}
final class B: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    var m: CBCentralManager!; var p: CBPeripheral?; var ch: [CBUUID: CBCharacteristic] = [:]
    var id = 0; var pendingId = 0; var sentAt = 0.0; var buf = Data(); var onReply: ((String) -> Void)?
    var latencies: [Double] = []; var framesSent = 0; var bytesSent = 0; var stream: [UInt8] = []; var inFlight = false
    var pumping = false; var start = 0.0; var chunk = 244; var seq = 0; var noResponse = false; var lastEpoch = -1; var healthTimes: [Double] = []; var lastHealth: [UInt8] = []
    override init() { super.init(); m = CBCentralManager(delegate: self, queue: nil) }
    func centralManagerDidUpdateState(_ c: CBCentralManager) { if c.state == .poweredOn { c.scanForPeripherals(withServices: [svc]) } }
    func centralManager(_ c: CBCentralManager, didDiscover per: CBPeripheral, advertisementData: [String: Any], rssi: NSNumber) { c.stopScan(); p = per; per.delegate = self; c.connect(per) }
    func centralManager(_ c: CBCentralManager, didConnect per: CBPeripheral) { per.discoverServices([svc]) }
    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral per: CBPeripheral, error: Error?) { say("desconectado \(String(describing: error))") }
    func peripheral(_ per: CBPeripheral, didDiscoverServices error: Error?) { for s in per.services ?? [] { per.discoverCharacteristics(nil, for: s) } }
    func peripheral(_ per: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        for c in s.characteristics ?? [] { ch[c.uuid] = c; say("caracteristica \(c.uuid.uuidString.prefix(8)) props 0x\(String(c.properties.rawValue, radix: 16))") }
        per.setNotifyValue(true, for: ch[rsp]!)
        if let h = ch[hlt] { per.setNotifyValue(true, for: h) }
        noResponse = ch[rtcmU]!.properties.contains(.writeWithoutResponse)
        say("RTCM \(noResponse ? "SIN" : "CON") respuesta")
        chunk = min(244, per.maximumWriteValueLength(for: .withoutResponse))
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.baseline(3)
        }
    }
    func request(_ method: String, _ path: String, _ body: String? = nil, _ done: @escaping (String) -> Void) {
        id += 1; pendingId = id; onReply = done; buf = Data(); sentAt = now()
        let json = "{\"id\":\(id),\"method\":\"\(method)\",\"path\":\"\(path)\"" + (body.map { ",\"body\":\($0)" } ?? "") + "}\n"
        let d = json.data(using: .utf8)!; var i = 0
        while i < d.count { p!.writeValue(d.subdata(in: i..<min(i + chunk, d.count)), for: ch[cmd]!, type: .withResponse); i += chunk }
    }
    // Latencia de órdenes sin RTCM, n veces.
    func baseline(_ n: Int) {
        if n == 0 { say("--- modo \(mode), RTCM \(noResponse ? "sin" : "con") respuesta, \(seconds) s, órdenes cada 250 ms ---"); pumping = true; start = now(); pump(); tickCommand(); return }
        request("GET", "/api/ble") { _ in say(String(format: "orden sin RTCM: %.0f ms", self.latencies.last! * 1000)); DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self.baseline(n - 1) } }
    }
    func tickCommand() {
        guard pumping else { return }
        request("GET", "/api/ble") { _ in say(String(format: "orden con RTCM: %.0f ms", self.latencies.last! * 1000)); DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { self.tickCommand() } }
    }
    func pump() {
        guard pumping, !inFlight else { return }
        if mode == "none" { if now() - start > seconds { pumping = false; finish() } else { DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { self.pump() } }; return }
        if now() - start > seconds { pumping = false; finish(); return }
        if (!noResponse || mode == "sat") && stream.count < chunk { let sizes = [520, 380, 300, 240, 180, 90, 40]; stream += frame(sizes[seq % sizes.count], seq); seq += 1; framesSent += 1 }
        if noResponse {
            // Una época de ~5 kB al empezar cada segundo, como un caster MSM7 pesado.
            let epoch = Int(now() - start)
            if mode == "burst" && epoch > lastEpoch {
                lastEpoch = epoch
                var left = epochBytes
                for size in [1000, 1000, 900, 800, 700, 300, 200, 60] where left > 0 { let s = min(size, left); stream += frame(s, seq); seq += 1; framesSent += 1; left -= s }
            }
            while pumping && !stream.isEmpty && p!.canSendWriteWithoutResponse && now() - start <= seconds {
                if mode == "sat" && stream.count < chunk { let sizes = [520, 380, 300, 240, 180, 90, 40]; stream += frame(sizes[seq % sizes.count], seq); seq += 1; framesSent += 1 }
                let piece = Array(stream.prefix(chunk)); stream.removeFirst(piece.count); bytesSent += piece.count
                p!.writeValue(Data(piece), for: ch[rtcmU]!, type: .withoutResponse)
            }
            if now() - start > seconds { pumping = false; finish(); return }
            if stream.isEmpty { DispatchQueue.main.asyncAfter(deadline: .now() + 0.02) { self.pump() } }
            return
        }
        let piece = Array(stream.prefix(chunk)); stream.removeFirst(piece.count); bytesSent += piece.count
        inFlight = true; p!.writeValue(Data(piece), for: ch[rtcmU]!, type: .withResponse)
    }
    func peripheralIsReady(toSendWriteWithoutResponse per: CBPeripheral) { pump() }
    func peripheral(_ per: CBPeripheral, didWriteValueFor c: CBCharacteristic, error: Error?) {
        if let e = error { say("error de escritura \(c.uuid.uuidString.prefix(8)): \(e)") }
        if c.uuid == rtcmU { inFlight = false; pump() }
    }
    func peripheral(_ per: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        if c.uuid == hlt, let v = c.value { healthTimes.append(now()); lastHealth = [UInt8](v); return }
        guard c.uuid == rsp, let v = c.value else { return }; let b = [UInt8](v)
        if b[4] & 1 != 0 { buf = Data() }; buf.append(contentsOf: b[5...])
        if b[4] & 2 != 0 { latencies.append(now() - sentAt); let s = String(data: buf, encoding: .utf8) ?? ""; let f = onReply; onReply = nil; f?(s) }
    }
    func finish() {
        let el = now() - start
        say(String(format: "RTCM: %d tramas (%d completas enviadas aprox.), %d bytes en %.1f s = %.0f B/s", framesSent, framesSent - (stream.isEmpty ? 0 : 1), bytesSent, el, Double(bytesSent) / el))
        let gaps = zip(healthTimes.dropFirst(), healthTimes).map { $0 - $1 }
        say(String(format: "salud: %d paquetes, intervalo min %.2f max %.2f s; ultimo %@", healthTimes.count, gaps.min() ?? 0, gaps.max() ?? 0, lastHealth.map { String(format: "%02x", $0) }.joined()))
        let l = latencies.sorted(); if !l.isEmpty { say(String(format: "ordenes: %d, p50 %.0f, max %.0f ms", l.count, l[l.count/2]*1000, l.last!*1000)) }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            self.request("GET", "/api/ble") { r in say("estado ble: \(r)")
                self.request("GET", "/api/status") { r in say("memoria: \(r.components(separatedBy: "\"memory\":").dropFirst().first?.prefix(330) ?? "?")")
                    self.m.cancelPeripheralConnection(self.p!); DispatchQueue.main.asyncAfter(deadline: .now() + 1) { exit(0) }
                }
            }
        }
    }
}
let b = B()
DispatchQueue.main.asyncAfter(deadline: .now() + seconds + 40) { say("tiempo agotado"); exit(2) }
RunLoop.main.run()
