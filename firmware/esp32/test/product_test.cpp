#include "product.h"
#include <cassert>
#include <cstdio>
#include <cstring>

// Los dos productos no pueden compartir ningún identificador que se vea en campo
// o que decida qué imagen se instala.
int main() {
    const product::Profile& v = product::kMeridianV;
    const product::Profile& m3 = product::kMeridian3;
    assert(std::strcmp(v.key, m3.key) != 0);
    assert(std::strcmp(v.name, m3.name) != 0);
    assert(std::strcmp(v.hostname, m3.hostname) != 0);
    assert(std::strcmp(v.hardwareId, m3.hardwareId) != 0);

    // El MeridianV conserva los identificadores de siempre: los equipos que ya
    // existen no cambian de nombre ni dejan de aceptar sus imágenes.
    assert(std::strcmp(v.name, "MeridianV") == 0);
    assert(std::strcmp(v.hostname, "meridianv") == 0);
    assert(std::strcmp(v.hardwareId, "tresvizo-esp32s3-4m-v1") == 0);

    // El Meridian3 no tiene nada de lo opcional.
    assert(!m3.microsd && !m3.imu && !m3.radio && !m3.battery && !m3.auxPort);
    assert(v.microsd && v.imu && v.radio && v.battery && v.auxPort);

#if defined(TRESVIZO_PRODUCT_MERIDIAN3)
    assert(std::strcmp(product::kCurrent.key, product::kMeridian3.key) == 0);
#else
    assert(std::strcmp(product::kCurrent.key, product::kMeridianV.key) == 0);
#endif
    std::puts("product_test: OK");
    return 0;
}
