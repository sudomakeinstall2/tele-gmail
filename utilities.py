import datetime
from email.utils import parsedate_tz, mktime_tz


def datetime_from_string_date( raw_date ):
    date_tuple = parsedate_tz(raw_date)
    date = datetime.datetime.utcfromtimestamp(mktime_tz(date_tuple))
    return date
