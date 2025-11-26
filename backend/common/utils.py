def to_bool(val):
    if isinstance(val, bool):
        return val
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return bool(val)
    s = str(val).strip().lower()
    if s in ('true', '1', 'yes', 'y', 'on', 't'):
        return True
    if s in ('false', '0', 'no', 'n', 'off', 'f'):
        return False
    return None

def parse_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def parse_decimal(val):
    try:
        from decimal import Decimal
        return Decimal(str(val))
    except Exception:
        return None

def parse_datetime(val):
    try:
        from django.utils.dateparse import parse_datetime as pd
        return pd(str(val))
    except Exception:
        return None

def parse_csv_ints(csv):
    if not csv:
        return []
    result = []
    for x in str(csv).split(','):
        x = x.strip()
        if not x:
            continue
        try:
            result.append(int(x))
        except Exception:
            pass
    return result
