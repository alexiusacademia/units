# units: writes tests/cases.json, the cases the library is checked
# against, with the answers pint gives. Run from the project folder:
#
#   python3 tools/oracle/oracle.py
#
# It needs pint (pip install pint). The registry is the one table.tsl is
# made from (tools/gen/registry.py). The cases:
#   names     every name in the table, prefixed and plural names, and junk,
#             found the way pint finds them
#   compound  units like "kN·m/s²" and "W/(m·K)", written several ways
#   convert   values converted between units of the same dimension,
#             temperatures and dB among them
#   read      sums and products of values with units, as typed
#   quantity  products, quotients, powers and sums of quantities
#
# Author: Alexius Academia
# Date: 2026-10-30

import json
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "gen"))
import registry as R  # noqa: E402

SEED = 20261030
IDENT = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def values_of(u, canonical, prefix_scale=1.0):
    factor, dims, (offset, logbase, logfactor) = R.unit_values(u, canonical)
    return {"factor": factor * prefix_scale, "dims": dims, "offset": offset,
            "logBase": logbase, "logFactor": logfactor}


def name_cases(rng):
    """Single names, as pint's get_name finds them, without letting pint
    add prefixed names to its table (which changes what it finds later)."""
    u = R.registry()
    keys = list(u._units.keys())
    pristine = set(keys)
    broken = set()
    for k in keys:
        try:
            R.unit_values(u, u._units[k].name)
        except Exception:
            broken.add(k)

    def expect(s):
        if s in pristine:
            if s in broken:
                return None
            return dict(ok=True, **values_of(u, u._units[s].name))
        cands = u.parse_unit_name(s)
        if not cands:
            return {"ok": False}
        prefix, unit, _ = cands[0]
        if unit in broken:
            return None
        if prefix:
            if not u._units[unit].is_multiplicative:
                return {"ok": False}
            scale = u._prefixes[prefix].converter.scale
            v = values_of(u, unit, scale)
            if v["logBase"] or v["offset"]:
                return {"ok": False}
            return dict(ok=True, **v)
        return dict(ok=True, **values_of(u, unit))

    texts = [k for k in keys if k not in broken]
    prefixes = [p for p in u._prefixes if p]
    simple = [k for k in keys if IDENT.match(k) and k not in broken]
    for _ in range(2500):
        s = rng.choice(prefixes) + rng.choice(simple)
        if rng.random() < 0.3:
            s += "s"
        texts.append(s)
    for _ in range(400):
        s = rng.choice(simple)
        if rng.random() < 0.5:
            s += "s"
        texts.append(s)
    letters = "abcdefghiklmnoprstuvwyzABCDGHJKLMNPRSTVW"
    for _ in range(700):
        texts.append("".join(rng.choice(letters) for _ in range(rng.randint(1, 4))))
    out = []
    seen = set()
    for s in texts:
        if s in seen or s in R.QUOTES:
            continue
        seen.add(s)
        e = expect(s)
        if e is None:
            continue
        if e["ok"] and not finite(e["factor"]):
            continue
        out.append(dict(text=s, **e))
    return out, simple


def pool(u, simple, rng):
    """Units to build compound units from: multiplicative, not log, with
    names pint's parser and ours both read the same way."""
    out = []
    for k in simple:
        d = u._units[k]
        if not d.is_multiplicative or type(d.converter).__name__ == "LogarithmicConverter":
            continue
        if k in ("pi", "π") or k[-1].isdigit():
            continue
        out.append(k)
    prefixes = ["k", "M", "m", "c", "µ", "G", "kilo", "milli", "mega"]
    for _ in range(300):
        s = rng.choice(prefixes) + rng.choice(out[:200])
        try:
            cands = u.parse_unit_name(s)
            if cands and cands[0][0] and u._units[cands[0][1]].is_multiplicative \
                    and type(u._units[cands[0][1]].converter).__name__ != "LogarithmicConverter":
                out.append(s)
        except Exception:
            pass
    return out


def power_text(p, rng, name):
    """Our text for a power, and pint's."""
    if p == 1:
        return "", ""
    if p == 0.5:
        return rng.choice(["^0.5", "**0.5"]), "**0.5"
    sup = {2: "²", 3: "³", -1: "⁻¹", -2: "⁻²", -3: "⁻³"}
    forms = ["^{}".format(p), "**{}".format(p), sup[p]]
    if p > 0 and not any(ch.isdigit() for ch in name):
        forms.append(str(p))
    return rng.choice(forms), "**{}".format(p)


def factor_text(rng, names):
    n = rng.choice(names)
    p = rng.choice([1, 1, 1, 1, 2, 3, -1, -2, 0.5])
    ours, theirs = power_text(p, rng, n)
    return n + ours, n + theirs, (n, p)


def compound_text(rng, names):
    """A random compound unit: our text, pint's, and its parts."""
    parts = []
    k = rng.randint(1, 3)
    ours = []
    theirs = []
    for i in range(k):
        o, t, part = factor_text(rng, names)
        ours.append(o)
        theirs.append(t)
        parts.append((part, 1))
    joiners = ["*", "·", " ", "·"]
    o_text = ours[0]
    for o in ours[1:]:
        j = rng.choice(joiners)
        o_text += j if j != " " else " "
        o_text += o if j != " " else o
    t_text = " * ".join(theirs)
    if rng.random() < 0.6:
        m = rng.randint(1, 2)
        dens_o = []
        dens_t = []
        for i in range(m):
            o, t, part = factor_text(rng, names)
            dens_o.append(o)
            dens_t.append(t)
            parts.append((part, -1))
        if m == 1:
            o_text += "/" + dens_o[0]
            t_text += " / " + dens_t[0]
        else:
            o_text += "/(" + rng.choice(["·", "*", " "]).join(dens_o) + ")"
            t_text += " / (" + " * ".join(dens_t) + ")"
    return o_text, t_text, parts


def si_of(u, text):
    q = u.Quantity(1.0, u.parse_units(text)).to_base_units()
    return q.magnitude, R.dims_vector(q.dimensionality)


def compound_cases(rng, simple):
    u = R.registry()
    names = pool(u, simple, rng)
    out = []
    while len(out) < 2500:
        o, t, _ = compound_text(rng, names)
        try:
            f, d = si_of(u, t)
        except Exception:
            continue
        if not finite(f) or f == 0:
            continue
        out.append({"text": o, "pint": t, "factor": f, "dims": d})
    return out, names


def same_dimension_swap(u, rng, name, by_dims):
    """Another unit with the same dimension as `name`, or `name`."""
    try:
        f, d = si_of(u, name)
    except Exception:
        return name
    group = by_dims.get(tuple(d), [name])
    return rng.choice(group)


def convert_cases(rng, names):
    u = R.registry()
    by_dims = {}
    for n in names:
        try:
            f, d = si_of(u, n)
            by_dims.setdefault(tuple(d), []).append(n)
        except Exception:
            pass
    groups = [g for g in by_dims.values() if len(g) >= 2]
    out = []
    # Simple units of the same dimension.
    while len(out) < 2000:
        g = rng.choice(groups)
        a, b = rng.choice(g), rng.choice(g)
        x = rng.choice([1.0, round(rng.uniform(-1000, 1000), 4), round(rng.uniform(0, 10), 6),
                        float("{:.4g}".format(10 ** rng.uniform(-6, 9)))])
        try:
            y = u.Quantity(x, a).to(b).magnitude
        except Exception:
            continue
        if finite(y):
            out.append({"x": x, "from": a, "to": b, "y": y})
    # Compound units, and the same with each part swapped for another of
    # its dimension.
    count = 0
    while count < 1000:
        o, t, parts = compound_text(rng, names)
        o2 = ""
        t2 = ""
        num_o = []
        den_o = []
        for (n, p), side in parts:
            m = same_dimension_swap(u, rng, n, by_dims)
            ours, theirs = power_text(p, rng, m)
            (num_o if side > 0 else den_o).append((m + ours, m + theirs))
        o2 = "·".join(x[0] for x in num_o)
        t2 = " * ".join(x[1] for x in num_o)
        if den_o:
            o2 += "/(" + "·".join(x[0] for x in den_o) + ")"
            t2 += " / (" + " * ".join(x[1] for x in den_o) + ")"
        x = round(rng.uniform(-500, 500), 3)
        try:
            y = u.Quantity(x, u.parse_units(t)).to(u.parse_units(t2)).magnitude
        except Exception:
            continue
        if finite(y):
            out.append({"x": x, "from": o, "to": o2, "y": y})
            count += 1
    # Temperatures and log units.
    temps = ["degC", "°C", "celsius", "degF", "°F", "fahrenheit", "K", "kelvin", "degR", "rankine", "degRe",
             "reaumur", "mK"]
    for _ in range(400):
        a, b = rng.choice(temps), rng.choice(temps)
        x = round(rng.uniform(-50, 400), 3)
        y = u.Quantity(x, a).to(b).magnitude
        out.append({"x": x, "from": a, "to": b, "y": y})
    logs = [("dBm", ["mW", "W", "kW", "µW", "dBW", "dBu", "dBm"]), ("dBW", ["W", "mW", "dBm"]),
            ("dBu", ["µW", "nW", "dBm"]), ("dB", ["dimensionless", "Np", "dB", "percent"]),
            ("Np", ["dimensionless", "dB"]), ("octave", ["dimensionless", "decade"]),
            ("decade", ["dimensionless", "octave"])]
    for _ in range(300):
        a, bs = rng.choice(logs)
        b = rng.choice(bs)
        x = round(rng.uniform(-30, 40), 3)
        flip = rng.random() < 0.5 and b not in ("dimensionless",)
        try:
            if flip:
                xx = abs(x) + 0.001
                y = u.Quantity(xx, b).to(a).magnitude
                out.append({"x": xx, "from": b, "to": a, "y": y})
            else:
                y = u.Quantity(x, a).to(b).magnitude
                out.append({"x": x, "from": a, "to": "" if b == "dimensionless" else b, "y": y})
        except Exception:
            continue
    return out, by_dims


def num_text(rng):
    r = rng.random()
    if r < 0.4:
        return str(rng.randint(1, 500))
    if r < 0.8:
        return "{:.3f}".format(rng.uniform(0.01, 100)).rstrip("0").rstrip(".")
    return "{:.2e}".format(rng.uniform(1, 9) * 10 ** rng.randint(-4, 6)).replace("e+0", "e").replace("e-0", "e-")


def read_cases(rng, by_dims):
    u = R.registry()
    groups = [g for g in by_dims.values() if len(g) >= 2]
    out = []
    while len(out) < 1500:
        g = rng.choice(groups)
        k = rng.randint(1, 3)
        ours = ""
        theirs = ""
        for i in range(k):
            n = num_text(rng)
            unit = rng.choice(g)
            if i > 0:
                op = rng.choice(["+", "-", "+"])
                ours += " {} ".format(op if op == "+" else rng.choice(["-", "−"]))
                theirs += " {} ".format(op)
            ours += "{} {}".format(n, unit) if rng.random() < 0.8 else "{}{}".format(n, unit)
            theirs += "({} * {})".format(n, unit)
        field = rng.choice(g) if rng.random() < 0.7 else ""
        try:
            q = u.parse_expression(theirs)
            if field:
                y = q.to(field).magnitude
                dims = R.dims_vector(q.dimensionality)
            else:
                b = q.to_base_units()
                y = b.magnitude
                dims = R.dims_vector(b.dimensionality)
        except Exception:
            continue
        if finite(y):
            out.append({"text": ours, "pint": theirs, "unit": field, "y": y, "dims": dims})
    # Products and quotients.
    names = [n for g in groups for n in g]
    while len(out) < 2100:
        a, b = rng.choice(names), rng.choice(names)
        na, nb = num_text(rng), num_text(rng)
        op = rng.choice(["*", "/", "·", "×", "÷"])
        pop = {"·": "*", "×": "*", "÷": "/"}.get(op, op)
        ours = "{} {} {} {} {}".format(na, a, op, nb, b)
        theirs = "({} * {}) {} ({} * {})".format(na, a, pop, nb, b)
        try:
            q = u.parse_expression(theirs).to_base_units()
        except Exception:
            continue
        if finite(q.magnitude):
            out.append({"text": ours, "pint": theirs, "unit": "", "y": q.magnitude,
                        "dims": R.dims_vector(q.dimensionality)})
    # Temperatures and dB levels on their own.
    for _ in range(150):
        a = rng.choice(["degC", "°C", "degF", "°F", "K", "degR"])
        f = rng.choice(["degC", "°C", "degF", "°F", "K", "degR"])
        x = round(rng.uniform(-40, 300), 2)
        y = u.Quantity(x, a).to(f).magnitude
        out.append({"text": "{} {}".format(x, a), "pint": "", "unit": f, "y": y,
                    "dims": R.dims_vector(u.Quantity(1, f).dimensionality)})
    for _ in range(100):
        a, f = rng.choice([("dBm", "mW"), ("dBm", "W"), ("dBW", "kW"), ("dB", "")])
        x = round(rng.uniform(-20, 30), 2)
        q = u.Quantity(x, a)
        y = q.to(f).magnitude if f else q.to("dimensionless").magnitude
        out.append({"text": "{} {}".format(x, a), "pint": "", "unit": f, "y": y,
                    "dims": R.dims_vector(q.to_base_units().dimensionality)})
    return out


def quantity_cases(rng, by_dims):
    u = R.registry()
    names = [n for g in by_dims.values() for n in g]
    out = []
    while len(out) < 1500:
        op = rng.choice(["times", "over", "power", "plus", "minus", "sqrt"])
        a = rng.choice(names)
        x = round(rng.uniform(0.1, 100), 4)
        b = rng.choice(by_dims[tuple(si_of(u, a)[1])]) if op in ("plus", "minus") else rng.choice(names)
        z = round(rng.uniform(0.1, 100), 4)
        p = rng.choice([2.0, 3.0, -1.0, 0.5, 1.5])
        try:
            qa = u.Quantity(x, a)
            qb = u.Quantity(z, b)
            r = {"times": lambda: qa * qb, "over": lambda: qa / qb, "power": lambda: qa ** p,
                 "plus": lambda: qa + qb, "minus": lambda: qa - qb, "sqrt": lambda: qa ** 0.5}[op]()
            r = r.to_base_units()
        except Exception:
            continue
        if finite(r.magnitude):
            out.append({"op": op, "x": x, "a": a, "z": z, "b": b, "p": p, "y": r.magnitude,
                        "dims": R.dims_vector(r.dimensionality)})
    return out


def main():
    import pint
    rng = random.Random(SEED)
    names, simple = name_cases(rng)
    compound, pool_names = compound_cases(rng, simple)
    convert, by_dims = convert_cases(rng, pool_names)
    read = read_cases(rng, by_dims)
    quantity = quantity_cases(rng, by_dims)
    cases = {"pint": pint.__version__, "seed": SEED, "names": names, "compound": compound,
             "convert": convert, "read": read, "quantity": quantity}
    path = os.path.join(ROOT, "tests", "cases.json")
    with open(path, "w") as f:
        json.dump(cases, f, ensure_ascii=False, separators=(",", ":"))
    ok = sum(1 for c in names if c["ok"])
    print("tests/cases.json: {} names ({} found), {} compound units, {} conversions, {} reads, {} quantities"
          .format(len(names), ok, len(compound), len(convert), len(read), len(quantity)))


if __name__ == "__main__":
    main()
