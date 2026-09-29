#pragma once

#include "nerdaxegaia.h"

// NerdAxe Gaia Pro: identische Hardware wie der Gaia, ab Werk hoeher
// getaktet (440 MHz / 1020 mV ~ 3 TH/s). Nur die Defaults unterscheiden
// sich, die gesamte Ansteuerung erbt vom Gaia.
class NerdaxeGaiaPro : public NerdaxeGaia {
  public:
    NerdaxeGaiaPro();
};
