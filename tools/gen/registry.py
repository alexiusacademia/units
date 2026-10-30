# units: the pint registry the library's table and test cases come from.
# It is pint's own default registry with three changes:
#   - an angle is its own dimension ([angle]), so rpm and Hz aren't mixed up;
#   - a bit is its own dimension ([information]);
#   - engineering units pint doesn't have (psf, pcf, cfs, gpm, MGD, ...).
# Each extra is checked to be a name pint didn't know before.
#
# Author: Alexius Academia
# Date: 2026-10-30

import os
import pint

# Engineering units pint doesn't define, in pint's own syntax.
EXTRAS = """
pound_force_per_square_foot = force_pound / foot ** 2 = psf
kip_per_square_foot = kip / foot ** 2 = ksf
ton_force_per_square_foot = 2000 * force_pound / foot ** 2 = tsf
pound_force_per_cubic_foot = force_pound / foot ** 3 = pcf
pound_force_per_cubic_inch = force_pound / inch ** 3 = pci
kip_per_cubic_foot = kip / foot ** 3 = kcf
kip_per_linear_foot = kip / foot = klf
pound_force_per_linear_foot = force_pound / foot = plf
cubic_foot_per_second = foot ** 3 / second = cfs = cusec
cubic_meter_per_second = meter ** 3 / second = cms = cumec
liter_per_second = liter / second = lps
liter_per_minute = liter / minute = lpm
gallon_per_minute = gallon / minute = gpm
gallon_per_day = gallon / day = gpd
million_gallons_per_day = 1e6 * gallon / day = MGD = mgd
million_cubic_meter = 1e6 * meter ** 3 = MCM
hectare_meter = hectare * meter = ha_m
inch_H2O = inch * water * g_0 = inH2O = in_H2O
meter_H2O = meter * water * g_0 = m_H2O
foot_per_minute = foot / minute = fpm
volt_ampere_reactive = volt * ampere = var
parts_per_billion = 1e-9 = ppb
dozen = 12
@alias acre_foot = ac_ft = acre_ft = acft
"""

# Names the library adds on top of the registry, which pint's parser can't
# take: ' and " for feet and inches.
QUOTES = {"'": "foot", '"': "inch"}

# The base dimensions, in the order the library keeps them.
BASE = ["length", "mass", "time", "temperature", "angle", "current",
        "substance", "luminosity", "information", "printing_unit"]


def pint_dir():
    return os.path.dirname(pint.__file__)


def definitions(extras=True):
    """pint's definitions with the changes above, as one text."""
    P = pint_dir()
    text = open(os.path.join(P, "default_en.txt")).read()
    for old, new in [("radian = [] = rad", "radian = [angle] = rad"),
                     ("bit = []", "bit = [information]")]:
        assert old in text, old
        text = text.replace(old, new)
    consts = open(os.path.join(P, "constants_en.txt")).read()
    text = text.replace("@import constants_en.txt", consts)
    if extras:
        # At the end, after the units they're made of.
        text = text + "\n# Engineering extras (units library)\n" + EXTRAS
    return text


def registry(extras=True, folder=None):
    folder = folder or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(folder, "_defs_extras.txt" if extras else "_defs_plain.txt")
    open(path, "w").write(definitions(extras))
    u = pint.UnitRegistry(path, autoconvert_offset_to_baseunit=False)
    os.remove(path)
    return u


def extra_names():
    """Every name the extras define, checked to be unknown to plain pint."""
    names = []
    for line in EXTRAS.strip().splitlines():
        if line.startswith("@alias"):
            parts = [p.strip() for p in line[len("@alias"):].split("=")]
            names += parts[1:]
        else:
            parts = [p.strip() for p in line.split("=")]
            names += [parts[0]] + parts[2:]
    return names


def check_extras():
    plain = registry(extras=False)
    known = []
    for n in extra_names():
        try:
            plain.parse_units(n)
            known.append(n)
        except Exception:
            pass
    assert not known, f"pint already knows {known}"


def dims_vector(dimensionality):
    """pint's dimensionality as a list in BASE order (floats: some old cgs
    units have half powers)."""
    v = [0.0] * len(BASE)
    for k, p in dict(dimensionality).items():
        name = k.strip("[]")
        v[BASE.index(name)] = float(p)
    return v


def unit_values(u, name):
    """A table unit's (factor, dims, (offset, log base, log factor)): SI =
    x × factor + offset, or factor × logbase^(x / logfactor) for log units."""
    d = u._units[name]
    conv = d.converter
    kind = type(conv).__name__
    if kind == "LogarithmicConverter":
        ref = u.Quantity(1.0, d.reference).to_base_units()
        return conv.scale * ref.magnitude, dims_vector(ref.dimensionality), (0.0, conv.logbase, conv.logfactor)
    q1 = u.Quantity(1.0, name)
    dims = dims_vector(q1.dimensionality)
    if kind == "OffsetConverter" and conv.offset != 0:
        # SI = x × scale × ref + offset × ref, ref being the reference
        # unit's factor (kelvin's: 1).
        ref = u.Quantity(1.0, d.reference).to_base_units().magnitude
        return conv.scale * ref, dims, (conv.offset * ref, 0.0, 0.0)
    return q1.to_base_units().magnitude, dims, (0.0, 0.0, 0.0)
