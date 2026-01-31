"""
A shameful display. This rips off python Lib/difflib.py.
"""

from difflib import *
from enum import Enum, unique


def _center(a: str, n: int, ws: str = " "):
    r = n // 2
    l = n - r
    return " " * l + a + " " * r


TRIMKEEP = 7
TRIMBREAK = "\x00"


def _midtrim(s: str, rm: int, pos: int, keep: int = TRIMKEEP):
    """
    Replace s[-rm:] with s[-rm:-rm+keep] + TRIMBREAK + s[-keep:],
    of course doing nothing when rm <= keep * 2 + 1

    POS is the real offset
    """
    if rm <= keep * 2 + 1:
        return s
    return (
        s[:-rm]
        + s[-rm : -rm + keep]
        + f"<{pos - rm + keep}{TRIMBREAK}{pos - keep}>"
        + s[-keep:]
    )


def _headtrim(s: str, rm: int, pos: int, keep: int = TRIMKEEP):
    if rm <= keep:
        return s
    # note: pos should be len s
    return f"{pos - keep}>" + s[-keep:]


def _tailtrim(s: str, rm: int, pos: int, keep: int = TRIMKEEP):
    if rm <= keep:
        return s
    return s[:-rm] + s[-rm : -rm + keep] + f"<{pos - rm + keep}"


@unique
class TrimOpts(int, Enum):
    NO = 0
    ENDS = 1
    ALL = 2


class Differ2:
    r"""
    Like Differ, but we work on the character level.
    """

    def __init__(self, linejunk=IS_LINE_JUNK, charjunk=IS_CHARACTER_JUNK):
        self.linejunk = linejunk
        self.charjunk = charjunk
        self.align_a = ""
        self.align_b = ""
        self.align_m = ""
        self.pos = 0

    def _dotrim(self, n, pos, f=_midtrim, k=TRIMKEEP):
        self.align_a = f(self.align_a, n, pos, k)
        self.align_b = f(self.align_b, n, pos, k)
        self.align_m = f(self.align_m, n, pos, k)

    def compare(self, a, b, trim=0):
        cruncher = SequenceMatcher(self.linejunk, a, b, autojunk=False)
        seen_nonequal = False
        ops = cruncher.get_opcodes()
        score = cruncher.ratio()

        self.align_a = ""
        self.align_b = ""
        self.align_m = ""
        pos = 0
        eq_run = 0

        for i, op in enumerate(ops):
            tag, alo, ahi, blo, bhi = op
            lap, lbp = ahi - alo, bhi - blo
            lmax = max(lap, lbp)
            if tag == "equal":
                self.align_a += "".join(a[alo:ahi])
                self.align_b += "".join(a[alo:ahi])
                self.align_m += " " * lap
                eq_run += lap
                pos += lmax
                continue

            if trim and eq_run:
                if not seen_nonequal:
                    self._dotrim(eq_run, pos, _headtrim)
                elif trim == TrimOpts.ALL:
                    self._dotrim(eq_run, pos, _midtrim)
                eq_run = 0

            seen_nonequal = True
            pos += lmax
            if tag == "delete":
                self.align_a += "".join(a[alo:ahi])
                self.align_b += " " * lap
                self.align_m += "-" * lap
            elif tag == "insert":
                seen_nonequal = True
                self.align_a += " " * lbp
                self.align_b += "".join(b[blo:bhi])
                self.align_m += "+" * lbp
            elif tag == "replace":
                seen_nonequal = True
                self.align_m += "^" * lmax
                self.align_a += _center("".join(a[alo:ahi]), lmax - lap)
                self.align_b += _center("".join(b[blo:bhi]), lmax - lbp)
            else:
                raise ValueError("unknown tag %r" % (tag,))

        if trim and eq_run:
            self._dotrim(eq_run, pos, _tailtrim)

        return (score, self.align_a, self.align_b, self.align_m)


def wrap(s: str, prefix: str = "", n: int = 118):
    ret = []
    for i in range(0, len(s), n):
        cand = s[i : i + n]
        for piece in cand.split(TRIMBREAK):
            ret.append(prefix + piece)
    return ret


def sndiff(a, b, linejunk=None, charjunk=None):
    differ = Differ2(linejunk, charjunk)
    score, a, b, m = differ.compare(a, b, TrimOpts.ALL)
    al, bl, ml = (wrap(a, "- "), wrap(b, "+ "), wrap(m, "? "))
    out = (
        "\n".join(
            "\n".join((a, b, m, "")) if not (a == b == m == "") else ""
            for a, b, m in zip(al, bl, ml)
        )
        if score < 1.0
        else ""
    )
    return (score, out)


if __name__ == "__main__":
    import sys

    s, e = sndiff(sys.argv[1], sys.argv[2])
    print(s)
    print(e)
