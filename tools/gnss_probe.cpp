// Lector de banco USB, macOS/POSIX. Reutiliza el parser del firmware.
#include "nmea_gga.h"
#include <chrono>
#include <cstdio>
#include <fcntl.h>
#include <fstream>
#include <poll.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

static uint64_t nowUs() {
    return std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
struct Port {
    int fd = -1;
    termios original{};
    bool restore = false;
    ~Port() { if (fd >= 0) { if (restore) tcsetattr(fd, TCSANOW, &original); close(fd); } }
};
int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr, "Uso: gnss_probe /dev/cu.PUERTO captura-local.nmea\nLectura pasiva 60 s, 115200 baud. No envía comandos.\n");
        return 1;
    }
    // El ESP32 usa una consola JSON; nunca confundirlo con el GNSS.
    if (!std::strncmp(argv[1], "/dev/cu.usbmodem", 16)) {
        std::fprintf(stderr, "Puerto usbmodem rechazado: verificar identidad antes de usar como GNSS.\n"); return 1;
    }
    Port port;
    port.fd = open(argv[1], O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (port.fd < 0 || ioctl(port.fd, TIOCEXCL) < 0 || tcgetattr(port.fd, &port.original) < 0) {
        std::perror("Abrir puerto exclusivo"); return 1;
    }
    port.restore = true;
    termios config = port.original;
    cfmakeraw(&config);
    cfsetspeed(&config, B115200);
    config.c_cflag |= CLOCAL | CREAD;
    config.c_cflag &= ~(CSIZE | PARENB | CSTOPB);
    config.c_cflag |= CS8;
#ifdef CRTSCTS
    config.c_cflag &= ~CRTSCTS;
#endif
    if (tcsetattr(port.fd, TCSANOW, &config) < 0) { std::perror("Configurar UART"); return 1; }
    // No sobrescribir capturas existentes.
    const int capture = open(argv[2], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (capture < 0) { std::perror("Crear captura"); return 1; }
    gnss::GgaParser parser;
    gnss::Gga sample;
    uint64_t bytes = 0, fresh = 0, duplicates = 0, discontinuities = 0;
    uint64_t epochSpan = 0, firstArrival = 0, lastArrival = 0, maxArrivalGap = 0;
    uint32_t previousUtc = 0;
    bool haveUtc = false, failed = false;
    const uint64_t started = nowUs();
    uint64_t reportAt = started;
    while (nowUs() - started < 60000000) {
        pollfd pending{port.fd, POLLIN, 0};
        const int ready = poll(&pending, 1, 250);
        if (ready < 0 || pending.revents & (POLLERR | POLLHUP | POLLNVAL)) { failed = true; break; }
        if (pending.revents & POLLIN) {
            char buffer[4096];
            const auto n = read(port.fd, buffer, sizeof(buffer));
            if (n <= 0) { failed = true; break; }
            bytes += n;
            ssize_t saved = 0;
            while (saved < n) {
                const auto count = write(capture, buffer + saved, n - saved);
                if (count <= 0) { failed = true; break; }
                saved += count;
            }
            if (failed) break;
            const uint64_t received = nowUs();
            for (ssize_t i = 0; i < n; ++i) if (parser.feed(buffer[i], received, sample) && sample.has_utc) {
                if (haveUtc) {
                    int64_t delta = static_cast<int64_t>(sample.utc_ms) - previousUtc;
                    if (previousUtc >= 86399000 && sample.utc_ms < 1000) delta += 86400000;
                    if (!delta) { ++duplicates; continue; }
                    if (delta < 0 || delta > 10000) { ++discontinuities; haveUtc = false; }
                    else epochSpan += delta;
                }
                if (!haveUtc) {
                    // New segment: no inferred continuity through clock jumps/restarts.
                    fresh = 0; epochSpan = 0; firstArrival = received; maxArrivalGap = 0;
                } else if (received - lastArrival > maxArrivalGap) maxArrivalGap = received - lastArrival;
                ++fresh; lastArrival = received; previousUtc = sample.utc_ms; haveUtc = true;
            }
        }
        if (nowUs() - reportAt >= 1000000) {
            reportAt = nowUs();
            std::printf("bytes=%llu gga=%u rechazadas=%u desbordes=%u epocas=%llu duplicadas=%llu saltos=%llu hz_epocas=%.2f hz_llegada=%.2f max_intervalo_llegada_ms=%.1f calidad=%u satelites=%d antiguedad_ms=%.0f\n",
                (unsigned long long)bytes, parser.accepted, parser.rejected, parser.overflow,
                (unsigned long long)fresh, (unsigned long long)duplicates, (unsigned long long)discontinuities,
                epochSpan ? (fresh-1)*1000.0/epochSpan : 0,
                lastArrival > firstArrival ? (fresh-1)*1000000.0/(lastArrival-firstArrival) : 0,
                maxArrivalGap/1000.0, sample.quality, sample.has_satellites ? static_cast<int>(sample.satellites) : -1,
                parser.accepted ? (reportAt-sample.arrival_us)/1000.0 : -1);
            std::fflush(stdout);
        }
    }
    if (fsync(capture) < 0) failed = true;
    if (close(capture) < 0) failed = true;
    if (failed) { std::fprintf(stderr, "Captura interrumpida por error de puerto o archivo.\n"); return 1; }
    return parser.accepted ? 0 : 2;
}
