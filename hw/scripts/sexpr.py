"""Minimal s-expression reader/writer for KiCad files (symbols, footprints, schematics).

Atoms come back as str; quoted atoms as Q (a str subclass) so they are written back quoted.
"""


class Q(str):
    """A quoted string atom."""


def parse(text):
    stack, cur, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "(":
            stack.append(cur)
            cur = []
            i += 1
        elif c == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while text[j] != '"':
                if text[j] == "\\":
                    j += 1
                    buf.append({"n": "\n", "t": "\t"}.get(text[j], text[j]))
                else:
                    buf.append(text[j])
                j += 1
            cur.append(Q("".join(buf)))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            cur.append(text[i:j])
            i = j
    return cur[0]


def quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def dump(x, indent=0):
    if isinstance(x, Q):
        return quote(x)
    if isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return fmt_num(x)
    flat = all(not isinstance(e, list) for e in x)
    if flat:
        return "(" + " ".join(dump(e) for e in x) + ")"
    pad = "\t" * (indent + 1)
    head = [dump(e) for e in x[:1]]
    out = "(" + " ".join(head)
    for e in x[1:]:
        out += "\n" + pad + dump(e, indent + 1) if isinstance(e, list) else " " + dump(e)
    return out + "\n" + "\t" * indent + ")"


def fmt_num(v):
    if isinstance(v, int):
        return str(v)
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def find(x, key):
    """First child list whose head is key."""
    for e in x:
        if isinstance(e, list) and e and e[0] == key:
            return e
    return None


def find_all(x, key):
    return [e for e in x if isinstance(e, list) and e and e[0] == key]
