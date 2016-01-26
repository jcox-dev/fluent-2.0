"""
    CLDR plural rules according to http://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html

    We have language rules in a handy `plurls.xml` but until someone takes a weekend on a fun project writing a proper
    parser for those rules, we simply type them out by hand.

"""
ZERO, ONE, TWO, FEW, MANY, OTHER = 'zotfmh'
LANGUAGE_LOOKUPS = {}

def _parse_value(value):
    """
    default: return source;
    case i: return integerValue;
    case f: return decimalDigits;
    case t: return decimalDigitsWithoutTrailingZeros;
    case v: return visibleDecimalDigitCount;
    case w: return visibleDecimalDigitCountWithoutTrailingZeros;
    FIXME: provide correct values 'WithoutTrailingZeroes' if argument is a Decimal
    """
    # Values that aren't set in the template will raise an exception when trying to cast to int
    # So we assume 1 for empty strings being passed in
    if value == '':
        value = 1

    if isinstance(value, (int, long)):
        return value, value, 0, 0, 0, 0

    str_value = repr(value).split('.')
    if len(str_value) == 2:
        decimals = len(str_value[1])
        f = int(str_value[1])
    else:
        decimals = f = 0
    return (
        value,          # n
        int(value),     # i
        f,              # f
        f,              # t
        decimals,       # v
        decimals,       # w
    )

def needs(*args):
    """ Decorate the function with a .needs attr
        defining which plurals forms it requires
    """
    def _decorator(f):
        f.plurals_needed = args
        return f
    return _decorator

def lookup(*langs):
    global LANGUAGE_LOOKUPS
    def _decorator(f):
        for l in langs:
            LANGUAGE_LOOKUPS[l] = f
        return f
    return _decorator

@needs(OTHER)
@lookup('zh', 'vi', 'id', 'th', 'ja', 'ko')
def l_no_plurals(n):
    return OTHER

@needs(ONE, OTHER)
@lookup('el', 'es', 'no', 'nb', 'tr', 'bg', 'hu')
def l_one_or_many(n):
    return ONE if n == 1 else OTHER

@needs(ONE, OTHER)
@lookup('ca', 'de', 'en', 'et', 'fi', 'it', 'nl', 'sv')
def l_one_or_many_or_fraction(n):
    n,i,f,t,v,w = _parse_value(n)
    if i == 1 and v == 0:
        return ONE
    return OTHER

@needs(ONE, OTHER)
@lookup('fr')
def fr_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    return ONE if i in (0,1) else OTHER

@needs(ONE, FEW, MANY, OTHER)
@lookup('pl')
def pl_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if v != 0:
        return OTHER
    if i == 1:
        return ONE
    elif 2 <= (i%10) <= 4 and not (12 <= (i%100) <= 14):
        return FEW
    elif (
        (i != 1 and 0<= i % 10 <= 1) or
        (5 <= i%10 <= 9) or
        (12 <= i%100 <= 14)
        ):
        return MANY

    return OTHER

@needs(ZERO, ONE, TWO, FEW, MANY, OTHER)
@lookup('ar')
def ar_lookup(n):
    if n == 0:
        return ZERO
    elif n == 1:
        return ONE
    elif n == 2:
        return TWO
    elif 3 <= n%100 <= 10:
        return FEW
    elif 11 <= n%100 <= 99:
        return MANY
    return OTHER

@needs(ONE, TWO, MANY, OTHER)
@lookup('he', 'iw')
def he_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if v != 0:
        return OTHER
    if i == 1:
        return ONE
    elif i == 2:
        return TWO
    elif n%10 == 0 and not 0 <= n <= 10:
        return MANY
    return OTHER

@needs(ZERO, ONE, OTHER)
@lookup('lv')
def lv_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if n%10 == 0 or 11<= n%100 <= 19 or (v ==2 and 11 <= f%100 <= 19):
        return ZERO
    elif (
        (n%10 == 1 and n%100 != 11)
        or (v == 2 and f%10 == 1 and f%100 != 11)
        or (v != 2 and f%10 == 1)
        ):
        return ONE
    return OTHER

@needs(ONE, FEW, OTHER)
@lookup('mo', 'ro')
def mo_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if i == 1 and v == 0:
        return ONE
    elif v != 0 or n == 0 or (n != 1 and 1<= n%100 <= 19):
        return FEW
    return OTHER

@needs(ONE, FEW, MANY, OTHER)
@lookup('lt')
def lt_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if n%10 == 1 and not 11<= n%100 <= 19:
        return ONE
    elif 2 <= n%10 <= 9 and not 11 <= n%100 <= 19:
        return FEW
    elif f != 0:
        return MANY
    return OTHER

@needs(ONE, FEW, MANY, OTHER)
@lookup('cs', 'sk')
def cs_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if i == 1 and v == 0:
        return ONE
    elif 2 <= i <= 4 and v == 0:
        return FEW
    elif v != 0:
        return MANY
    return OTHER

@needs(ONE, TWO, FEW, OTHER)
@lookup('sl')
def sl_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if v == 0 and i%100 == 1:
        return ONE
    elif v == 0 and i%100 == 2:
        return TWO
    elif (v == 0 and 3 <= i%100 <= 4) or v != 0:
        return FEW
    return OTHER

@needs(ONE, OTHER)
@lookup('fil', 'tl')
def tl_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if v == 0 and (i == 0 or i == 1):
        return ONE
    return OTHER

@needs(ONE, OTHER)
@lookup('pt')
def pt_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if i == 1 and v == 0 or i == 0 and t == 1:
        return ONE
    return OTHER

@needs(ONE, OTHER)
@lookup('da')
def da_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if n == 1 or t != 0 and (i == 0 or i == 1):
        return ONE
    return OTHER

@needs(ONE, OTHER)
@lookup('hi')
def hi_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if i == 0 or n == 1:
        return ONE
    return OTHER

@needs(ONE, OTHER)
@lookup('si')
def si_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if n == 0 or n == 1 or (i == 0 and f == 1):
        return ONE
    return OTHER

@needs(ONE, FEW, OTHER)
@lookup('hr', 'sr')
def hr_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if (
        (v == 0 and i%10 == 1 and i%100 != 11)
        or (f%10 == 1 and f%100 != 11)
        ):
        return ONE
    elif (
        (v == 0 and 2 <= i%10 <= 4 and 12 <= i%100 <= 14)
        or (2 <= f%10 <= 4 and not (12 <= f%100 <= 14))
        ):
        return FEW
    return OTHER

@needs(ONE, MANY, OTHER)
@lookup('ru')
def ru_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if v != 0:
        return OTHER
    if i%10 == 1 and i%100 != 11:
        return ONE
    elif i%10 == 0 or 5 <= i%10 <= 9 or 11 <= i%100 <= 14:
        return MANY
    return OTHER

@needs(ONE, FEW, MANY, OTHER)
@lookup('uk')
def uk_lookup(n):
    n,i,f,t,v,w = _parse_value(n)
    if v != 0:
        return OTHER
    if i%10 == 1 and i%100 != 11:
        return ONE
    elif 2 <= i%10 <= 4 and not 12 <= i%100 <= 14:
        return FEW
    elif i%10 == 0 or 5 <= i%10 <= 9 or 11 <= i%100 <= 14:
        return MANY
    return OTHER

"""
Rules in JSON for 43 G's languages:
{"el": [["one", "n = 1"], ["other", ""]], "en": [["one", "i = 1 and  v = 0"], ["other", ""]], "zh": [["other", ""]], "vi": [["other", ""]], "ca": [["one", "i = 1 and  v = 0"], ["other", ""]], "it": [["one", "i = 1 and  v = 0"], ["other", ""]], "iw": [["one", "i = 1 and  v = 0"], ["two", "i = 2 and  v = 0"], ["many", "v = 0 and  n != 0..10 and  n % 10 = 0"], ["other", ""]], "ar": [["zero", "n = 0"], ["one", "n = 1"], ["two", "n = 2"], ["few", "n % 100 = 3..10"], ["many", "n % 100 = 11..99"], ["other", ""]], "cs": [["one", "i = 1 and  v = 0"], ["few", "i = 2..4 and  v = 0"], ["many", "v != 0"], ["other", ""]], "et": [["one", "i = 1 and  v = 0"], ["other", ""]], "id": [["other", ""]], "es": [["one", "n = 1"], ["other", ""]], "ru": [["one", "v = 0 and  i % 10 = 1 and  i % 100 != 11"], ["many", "v = 0 and  i % 10 = 0 orv = 0 and  i % 10 = 5..9 orv = 0 and  i % 100 = 11..14"], ["other", ""]], "nl": [["one", "i = 1 and  v = 0"], ["other", ""]], "pt": [["one", "i = 1 and  v = 0 ori = 0 and  t = 1"], ["other", ""]], "no": [["one", "n = 1"], ["other", ""]], "nb": [["one", "n = 1"], ["other", ""]], "tr": [["one", "n = 1"], ["other", ""]], "lt": [["one", "n % 10 = 1 and  n % 100 != 11..19"], ["few", "n % 10 = 2..9 and  n % 100 != 11..19"], ["many", "f != 0"], ["other", ""]], "lv": [["zero", "n % 10 = 0 orn % 100 = 11..19 orv = 2 and  f % 100 = 11..19"], ["one", "n % 10 = 1 and  n % 100 != 11 orv = 2 and  f % 10 = 1 and  f % 100 != 11 orv != 2 and  f % 10 = 1"], ["other", ""]], "tl": [["one", "i = 0..1 and  v = 0"], ["other", ""]], "th": [["other", ""]], "ro": [["one", "i = 1 and  v = 0"], ["few", "v != 0 orn = 0 orn != 1 and  n % 100 = 1..19"], ["other", ""]], "pl": [["one", "i = 1 and  v = 0"], ["few", "v = 0 and  i % 10 = 2..4 and  i % 100 != 12..14"], ["many", "v = 0 and  i != 1 and  i % 10 = 0..1 orv = 0 and  i % 10 = 5..9 orv = 0 and  i % 100 = 12..14"], ["other", ""]], "fr": [["one", "i = 0,1"], ["other", ""]], "bg": [["one", "n = 1"], ["other", ""]], "hr": [["one", "v = 0 and  i % 10 = 1 and  i % 100 != 11 orf % 10 = 1 and  f % 100 != 11"], ["few", "v = 0 and  i % 10 = 2..4 and  i % 100 != 12..14 orf % 10 = 2..4 and  f % 100 != 12..14"], ["other", ""]], "de": [["one", "i = 1 and  v = 0"], ["other", ""]], "da": [["one", "n = 1 ort != 0 and  i = 0,1"], ["other", ""]], "hi": [["one", "i = 0 orn = 1"], ["other", ""]], "fi": [["one", "i = 1 and  v = 0"], ["other", ""]], "hu": [["one", "n = 1"], ["other", ""]], "ja": [["other", ""]], "he": [["one", "i = 1 and  v = 0"], ["two", "i = 2 and  v = 0"], ["many", "v = 0 and  n != 0..10 and  n % 10 = 0"], ["other", ""]], "sr": [["one", "v = 0 and  i % 10 = 1 and  i % 100 != 11 orf % 10 = 1 and  f % 100 != 11"], ["few", "v = 0 and  i % 10 = 2..4 and  i % 100 != 12..14 orf % 10 = 2..4 and  f % 100 != 12..14"], ["other", ""]], "mo": [["one", "i = 1 and  v = 0"], ["few", "v != 0 orn = 0 orn != 1 and  n % 100 = 1..19"], ["other", ""]], "ko": [["other", ""]], "sv": [["one", "i = 1 and  v = 0"], ["other", ""]], "sk": [["one", "i = 1 and  v = 0"], ["few", "i = 2..4 and  v = 0"], ["many", "v != 0"], ["other", ""]], "si": [["one", "n = 0,1 ori = 0 and  f = 1"], ["other", ""]], "fil": [["one", "i = 0..1 and  v = 0"], ["other", ""]], "uk": [["one", "v = 0 and  i % 10 = 1 and  i % 100 != 11"], ["few", "v = 0 and  i % 10 = 2..4 and  i % 100 != 12..14"], ["many", "v = 0 and  i % 10 = 0 orv = 0 and  i % 10 = 5..9 orv = 0 and  i % 100 = 11..14"], ["other", ""]], "sl": [["one", "v = 0 and  i % 100 = 1"], ["two", "v = 0 and  i % 100 = 2"], ["few", "v = 0 and  i % 100 = 3..4 orv != 0"], ["other", ""]]}
"""

# Dummy implementation, just for tests, the real one will go directly inside our .utils._get_trans
def _default(value): return OTHER
def get_plural_index(language_code, value):
    return LANGUAGE_LOOKUPS.get(language_code.split("-")[0].lower(), _default)(value)
