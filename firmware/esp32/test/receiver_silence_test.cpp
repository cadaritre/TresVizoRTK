// Alarma `receiver_silent` (include/receiver_silence.h).
#include "receiver_silence.h"
#include <cassert>

int main() {
    using namespace receiver_silence;
    // Sin UART no hay alarma de receptor mudo (la da `uart_failed`).
    assert(!silent(false, 0, 0));
    assert(!silent(false, 100, kSilentAfterUs * 10));
    // Nunca llegó una GGA desde el arranque.
    assert(silent(true, 0, 0));
    // F05: llegaron muchas y dejaron de llegar en esta sesión. Antes, con el
    // contador en 1234, no saltaba hasta reiniciar.
    assert(silent(true, 1234, kSilentAfterUs + 1));
    assert(!silent(true, 1234, kSilentAfterUs));
    // A 1 Hz, una o dos épocas perdidas no son silencio.
    assert(!silent(true, 1234, 2000000));
    return 0;
}
