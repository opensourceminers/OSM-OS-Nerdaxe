#include "nerdaxegaiapro.h"

NerdaxeGaiaPro::NerdaxeGaiaPro() : NerdaxeGaia() {
    m_deviceModel = "NerdAxeGaiaPro";

    // Werksseitig hoeher getaktet als der Gaia: ~3 TH/s.
    m_defaultAsicFrequency = m_asicFrequency = 440;
    m_defaultAsicVoltageMillis = m_asicVoltageMillis = 1020;
}
