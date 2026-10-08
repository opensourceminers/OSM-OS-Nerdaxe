#include "nerdaxegaiapro.h"

// OSM-Variante: KEINE eigene Hardware, sondern der normale (einphasige) Gaia
// mit groesserem Kuehler und hoeherem Auslieferungstakt. Deshalb bleibt die
// Konfiguration des Spannungsreglers unveraendert die des Gaia:
// 400 kHz Schaltfrequenz und 28/33 A Ueberstromgrenze fuer den einen
// TPS546D24A (40 A Typ). Die 2-Phasen-Werte der gleichnamigen Bitmaker-
// Entwicklung (650 kHz, 40/52 A) wuerden hier die Schutzschwelle ueber die
// Belastbarkeit des Bauteils heben und den Regelkreis verstimmen.
NerdaxeGaiaPro::NerdaxeGaiaPro() : NerdaxeGaia()
{
    m_deviceModel = "NerdAxeGaiaPro";

    // Nur der Auslieferungstakt unterscheidet sich vom Gaia; Frequenz- und
    // Spannungslisten bleiben die des Gaia (bis 440 MHz / 1040 mV).
    m_defaultAsicFrequency = m_asicFrequency = 440;
    m_defaultAsicVoltageMillis = m_asicVoltageMillis = 1020;

    // Der Gaia-Konstruktor setzt das Display-Theme nur unter NERDAXEGAIA.
    m_theme = new ThemeNerdaxegaia();
}
