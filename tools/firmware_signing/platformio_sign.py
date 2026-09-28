"""Tras compilar, firma firmware.bin como firmware-signed.bin al lado.

Script de PlatformIO (`extra_scripts = post:...` en firmware/esp32/platformio.ini).
Solo firma si la clave privada del propietario está en esta máquina
(TRESVIZO_SIGNING_KEY o ~/.tresvizo/firmware-signing/private.pem). Sin clave,
avisa y la compilación sigue: firmware.bin vale para cargar por USB, pero no por
OTA. Con clave, si la firma no verifica con la clave pública embebida en el
firmware, la compilación falla: ese archivo no lo instalaría ningún equipo.

La clave solo la abre `openssl`; este script no la lee, no la copia y no la
imprime (tampoco su ruta completa si viene de la variable de entorno).
"""
import importlib.util
from pathlib import Path

Import("env")  # noqa: F821 (lo define PlatformIO)

PROJECT = Path(env.subst("$PROJECT_DIR"))  # noqa: F821
TOOL = PROJECT.parents[1] / "tools" / "firmware_signing" / "sign_firmware.py"
spec = importlib.util.spec_from_file_location("tresvizo_sign_firmware", TOOL)
signer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signer)


def sign_after_build(source, target, env):
    firmware = Path(target[0].get_abspath())
    output = firmware.with_name("firmware-signed.bin")
    key = signer.default_key_path()
    if not key.is_file():
        # Uno viejo al lado parecería de esta compilación y no lo es.
        if output.exists():
            output.unlink()
        print("AVISO: no está la clave de firma del propietario "
              f"({signer.KEY_ENVIRONMENT} o {signer.DEFAULT_KEY}); no se generó firmware-signed.bin. "
              "firmware.bin sirve para cargar por USB, pero el equipo no lo acepta por OTA.")
        return None
    try:
        signed = signer.sign_file(firmware, output, key)
        valid, message = signer.verify(signed)
    except (signer.SigningError, OSError) as error:
        valid, message = False, str(error)
    if not valid:
        if output.exists():
            output.unlink()
        print(f"ERROR: no se pudo firmar firmware.bin: {message} "
              "Si la clave privada no es la del equipo, ningún Meridian V aceptaría el archivo.")
        return 1
    print(f"Firmado: {output} — {signer.describe(signed)}. Verificado con la clave embebida en el firmware. "
          "Es el archivo que se da a las apps y al panel.")
    return None


env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", sign_after_build)  # noqa: F821
