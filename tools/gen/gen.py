# units: writes table.tsl, the library's unit table, from pint's registry
# (see registry.py for the changes made to it). Run from the project folder:
#
#   python3 tools/gen/gen.py
#
# It needs pint (pip install pint). Every unit, prefix and named dimension
# pint knows goes into the table, worked out by pint itself: a unit's factor
# to SI base units, its dimension, and its offset (°C, °F) or log scale (dB).
#
# Author: Alexius Academia
# Date: 2026-10-30

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def tsl_string(s):
    out = s.replace("\\", "\\\\").replace('"', '\\"').replace("{", "\\{").replace("}", "\\}")
    return '"' + out + '"'


def tidy(x):
    """The shortest decimal within one rounding step of x: pint works a
    foot out as 12 × 0.0254 = 0.30479999999999996; that's 0.3048."""
    if x == 0 or not math.isfinite(x):
        return x
    for digits in range(1, 17):
        y = float(f"{x:.{digits}g}")
        if abs(y - x) <= math.ulp(x):
            return y
    return x


def num(x):
    x = tidy(float(x))
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    return repr(x)


def dims_text(v):
    return ",".join(num(p) for p in v)


def main():
    R.check_extras()
    import pint
    u = R.registry()

    # Units, grouped by their canonical name, keeping pint's order.
    groups = {}
    for key, d in u._units.items():
        groups.setdefault(d.name, []).append(key)

    # pint adds some prefixed units (kilometer, microgram) to its table while
    # it loads, in an order that changes from run to run: those go last,
    # sorted, so the table comes out the same every time.
    def made_by_prefix(name, keys):
        cands = u.parse_unit_name(name)
        return keys == [name] and bool(cands) and all(c[0] for c in cands)

    defined = [n for n, k in groups.items() if not made_by_prefix(n, k)]
    prefixed = sorted(n for n, k in groups.items() if made_by_prefix(n, k))

    rows = []
    skipped = []
    for name in defined + prefixed:
        keys = groups[name]
        d = u._units[name]
        try:
            factor, dims, extra = R.unit_values(u, name)
        except Exception as e:  # pint's own broken entries (R_∞)
            skipped.append((name, str(e)[:60]))
            continue
        if not math.isfinite(factor):
            skipped.append((name, "factor isn't finite"))
            continue
        symbol = d.symbol or name
        names = [name] + [k for k in keys if k != name]
        for q, target in R.QUOTES.items():
            if name == target:
                names.append(q)
        for k in names:
            assert "|" not in k and "," not in k, k
        rows.append("|".join([name, symbol, ",".join(names), num(factor), dims_text(dims),
                              num(extra[0]), num(extra[1]), num(extra[2])]))

    prefixes = []
    for key, p in u._prefixes.items():
        if key == "":
            continue
        prefixes.append(f"{key}|{num(p.converter.scale)}")

    named = []
    for key in u._dimensions:
        name = key.strip("[]")
        if name in R.BASE or name == "":
            continue
        try:
            v = R.dims_vector(u.get_dimensionality(key))
        except Exception as e:
            skipped.append((key, str(e)[:60]))
            continue
        named.append(f"{name}|{dims_text(v)}")

    out = []
    out.append("// units: every unit, prefix and named dimension, from pint "
               f"{pint.__version__}'s registry")
    out.append("// with an angle and a bit as dimensions of their own, and engineering extras.")
    out.append("// The definitions are pint's (© Hernan E. Grecco and contributors), under its")
    out.append("// BSD licence: see LICENSE-pint.")
    out.append("// Written by tools/gen/gen.py; don't edit it by hand.")
    out.append("//")
    out.append("// Author: Alexius Academia")
    out.append("// Date: 2026-10-30")
    out.append("")
    out.append("// The base dimensions, in the order of a dimension's powers.")
    out.append("let baseNames: [String] = [" + ", ".join(tsl_string(b) for b in R.BASE) + "]")
    out.append("")
    out.append("// A unit: name|symbol|all its names|factor to SI|powers of the base")
    out.append("// dimensions|offset (°C, °F)|log base|log factor (dB).")
    out.append("let unitRows: [String] = [")
    for r in rows:
        out.append("    " + tsl_string(r) + ",")
    out.append("]")
    out.append("")
    out.append("// Prefixes in the order pint tries them: name or symbol|factor.")
    out.append("let prefixRows: [String] = [")
    for r in prefixes:
        out.append("    " + tsl_string(r) + ",")
    out.append("]")
    out.append("")
    out.append("// Named dimensions beyond the base ones: name|powers.")
    out.append("let dimensionRows: [String] = [")
    for r in named:
        out.append("    " + tsl_string(r) + ",")
    out.append("]")
    open(os.path.join(ROOT, "table.tsl"), "w").write("\n".join(out) + "\n")
    names = sum(len(r.split("|")[2].split(",")) for r in rows)
    print(f"table.tsl: {len(rows)} units ({names} names), {len(prefixes)} prefixes, "
          f"{len(named)} named dimensions")
    if skipped:
        print("skipped:", skipped)


if __name__ == "__main__":
    main()
