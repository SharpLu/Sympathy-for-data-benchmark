import logging
import datetime


def error_message(message, error_where):
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    logging.error(
        u'{}  ERROR    {}    {}\n'.format(timestamp, error_where, message))


def warning_message(message, error_where):
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    logging.warning(
        u'{}  WARNING    {}    {}\n'.format(timestamp, error_where, message))
