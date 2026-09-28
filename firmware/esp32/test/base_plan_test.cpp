#include "base_plan.h"
#include <cassert>
#include <cmath>
#include <limits>
namespace {
bool near(double a, double b) { return std::fabs(a - b) < 1e-9; }
}
int main() {
 double arp;
 // La altura recibida es siempre la del punto en el suelo: la antena se suma
 // siempre. Desde 0.6.2 no se pregunta a qué punto corresponde la altura.
 assert(base_plan::known(0,0,100,2,arp) && arp==102);
 assert(base_plan::known(0,0,100,0,arp) && arp==100);
 assert(base_plan::known(-90,180,-100,0,arp));
 assert(!base_plan::known(91,0,100,2,arp));
 assert(!base_plan::known(0,-181,100,2,arp));
 assert(!base_plan::known(0,0,30000,2,arp));
 assert(!base_plan::known(0,0,100,-1,arp));
 assert(!base_plan::known(0,0,std::numeric_limits<double>::quiet_NaN(),0,arp));
 // El case es una constante declarada, no medida sobre la carcasa real.
 assert(base_plan::kCaseOffsetM > 0 && base_plan::kCaseOffsetM < 1);
 assert(base_plan::average(1,0) && base_plan::average(3600,10));
 assert(!base_plan::average(0,0) && !base_plan::average(3601,0) && !base_plan::average(1,-1));

 // --- Promedio del ESP32 (F02) ---
 // El case es la constante única del firmware; estos casos lo dan por 0.10.
 assert(base_plan::kCaseOffsetM == 0.10);
 const double nan = std::numeric_limits<double>::quiet_NaN();
 // GGA con UNDULATION 0.0000: altura 100.000, ondulación 0.
 assert(near(base_plan::ggaEllipsoidHeightM(100.0, 0.0), 100.0));
 // La misma antena con UNDULATION AUTO: 80.000 sobre el geoide + 20.000.
 assert(near(base_plan::ggaEllipsoidHeightM(80.0, 20.0), 100.0));
 // Sin ondulación informada se toma 0 (el estado lo advierte aparte).
 assert(near(base_plan::ggaEllipsoidHeightM(80.0, nan), 80.0));
 // Caso 100/0/2: se declara la media tal cual, 100.000, no 102.100; la marca
 // queda en 100 − 2 − 0.10 = 97.900.
 {
  const auto h = base_plan::surveyHeights(base_plan::ggaEllipsoidHeightM(100.0, 0.0), 2.0);
  assert(near(h.declaredEllipsoidHeightM, 100.0));
  assert(near(h.markEllipsoidHeightM, 97.9));
 }
 // Caso 80 + 20 de ondulación, antena 2: lo mismo.
 {
  const auto h = base_plan::surveyHeights(base_plan::ggaEllipsoidHeightM(80.0, 20.0), 2.0);
  assert(near(h.declaredEllipsoidHeightM, 100.0));
  assert(near(h.markEllipsoidHeightM, 97.9));
 }
 // Las dos rutas cuadran: la marca del promedio, metida como «la conozco» con
 // la misma antena, declara la misma altura que el promedio.
 {
  const auto h = base_plan::surveyHeights(100.0, 1.8);
  assert(base_plan::known(0, 0, h.markEllipsoidHeightM, 1.8, arp));
  assert(near(arp + base_plan::kCaseOffsetM, h.declaredEllipsoidHeightM));
 }
 // Sin antena la marca queda solo el case por debajo.
 assert(near(base_plan::surveyHeights(100.0, 0.0).markEllipsoidHeightM, 99.9));
}
