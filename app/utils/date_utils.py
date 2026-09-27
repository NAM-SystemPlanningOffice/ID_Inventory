from datetime import datetime, date

def parse_date(date_str, formats=None):
    if formats is None:
        formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']

    if isinstance(date_str, date):
        return date_str

    if isinstance(date_str, datetime):
        return date_str.date()

    for fmt in formats:
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Date format not recognized: {date_str}")

def format_date(d, fmt='%Y-%m-%d'):
    if d is None:
        return None
    if isinstance(d, str):
        d = parse_date(d)
    return d.strftime(fmt)

def generate_batch_id(system_id):
    return datetime.now().strftime(f'%Y%m%d_%H%M%S_{system_id}')
