"""
    POT files specify plural forms as a list, providing a Plural-Form expression specifying
    how to select the form based on the provided number.

    Currently fluent stores an expression for each language, but it's possible to evaluate that
    expression per pot file.

    Because the Plural-Forms use C-style ternaries we can't eval() them and provide a simple
    parser instead.


    This parser is based on Fredrik Lundh's (effbot.org) adaptation of Douglas Crockford's
    adaptation of Vaughan Pratt's topdown parser algorithm.
"""
import re


symbol_table = {}


class SymbolBase(object):
    id = None
    value = None
    first = second = third = None

    def nud(self, i):
        raise SyntaxError("Syntax error (%r)." % self.id)

    def led(self, i, left):
        raise SyntaxError("Unknown operator (%r)." % self.id)

    def __repr__(self):
        if self.id == "n":
            return "(var n)"
        elif self.id == "literal":
            return "(%s %s)" % (self.id, self.value)
        out = [self.id, self.first, self.second, self.third]
        out = map(str, filter(None, out))
        return "(" + " ".join(out) + ")"


def symbol(token, bp=0):
    try:
        S = symbol_table[token]
    except KeyError:
        class S(SymbolBase):
            pass
        S.__name__ = "symbol-" + token
        S.id = token
        S.value = None
        S.lbp = bp
        symbol_table[token] = S
    else:
        S.lbp = max(bp, S.lbp)
    return S


# helpers
def infix(id, bp):
    def led(self, i, left):
        self.first = left
        self.second = expression(i, bp)
        return self
    symbol(id, bp).led = led


def infix_r(id, bp):
    def led(self, i, left):
        self.first = left
        self.second = expression(i, bp-1)
        return self
    symbol(id, bp).led = led


def prefix(id, bp):
    def nud(self, i):
        self.first = expression(i, bp)
        return self
    symbol(id).nud = nud


def advance(i, id=None):
    if id and i.current.id != id:
        raise SyntaxError("Expected %r" % id)
    i.next()


def method(s):
    assert issubclass(s, SymbolBase)
    def bind(fn):
        setattr(s, fn.__name__, fn)
    return bind

# python expression syntax
infix_r("||", 30); infix_r("&&", 40);

infix("<", 60); infix("<=", 60)
infix(">", 60); infix(">=", 60)
infix("!=", 60); infix("==", 60) # infix("<>", 60);
#infix("+", 110); infix("-", 110)
#infix("*", 120); infix("/", 120); infix("//", 120)
infix("%", 120)
prefix("-", 130); prefix("+", 130); prefix("~", 130)

# additional behaviour
symbol("n").nud = lambda self, i: self
symbol("literal").nud = lambda self, i: self
symbol("end")


symbol(")")
@method(symbol("(", 150))
def nud(self, i):
    # parenthesized form; replaced by tuple former below
    expr = expression(i)
    advance(i, ")")
    return expr


# ternary form
symbol(":")
@method(symbol("?", 20))
def led(self, i, left):
    self.first = left
    self.second = expression(i)
    advance(i, ":")
    self.third = expression(i)
    return self


class tokenize(object):
    def __init__(self, str_expr):
        self.generator = self.split(str_expr)
        self.next()

    def next(self):
        self.current = self.generator.next()
        return self

    def split(self, str_expr):
        """ Simple tokenizer, only handling common operators from the gettext Plural-Form expressions. """
        TOKEN_PATTERN = r'\s*(?:(>=|<=|==|!=|&&|\|\||\W)|(n)|(\d+))'

        for op, var, literal in re.findall(TOKEN_PATTERN, str_expr):
            if literal:
                symbol = symbol_table["literal"]
                s = symbol()
                s.value = int(literal)
            elif var:
                symbol = symbol_table["n"]
                s = symbol()
            elif op:
                symbol = symbol_table[op]
                s = symbol()
            else:
                raise SyntaxError
            yield s
        yield symbol_table["end"]()
        yield None


# parser engine
def expression(i, rbp=0):
    left = i.current.nud(i.next())
    while rbp < i.current.lbp:
        left = i.current.led(i.next(), left)
    return left


def parse(str_expr):
    return expression(i=tokenize(str_expr))


def calculate(s, n):
    if s.id == "n":
        return n
    elif s.id == "literal":
        return s.value
    else:
        a = calculate(s.first, n)
        b = calculate(s.second, n)
        if s.id == "?":
            return b if a else calculate(s.third, n)

        return {
            "!=": lambda: a != b,
            "==": lambda: a == b,
            "&&": lambda: a and b,
            "||": lambda: a or b,
            ">=": lambda: a >= b,
            ">": lambda: a > b,
            "<=": lambda: a <= b,
            "<": lambda: a < b,
            "%": lambda: a % b,
        }[s.id]()

