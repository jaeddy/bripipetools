"""
Class for reading and parsing Picard metrics files.
"""
import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PicardMetricsFile(object):
    """
    Parser to read tables of metrics generated by one of several Picard tools,
    typically stored in an HTML file, and return as a parsed and formatted
    dictionary.
    """
    def __init__(self, path):
        self.path = path
        self.data = {}

    def _read_file(self):
        """
        Read file into raw HTML string.
        """
        logger.debug("reading file '{}' to raw HTML string".format(self.path))
        with open(self.path) as f:
            self.data['raw'] = f.read()

    def _get_table(self):
        """
        Extract metrics table from raw HTML string.
        """
        raw_html = self.data['raw']
        soup = BeautifulSoup(raw_html, 'html.parser')
        logger.debug("getting metrics table from raw HTML string")
        self.data['table'] = soup.findAll(
            'table', attrs={'cellpadding': '3'}
            )[0]

    def _check_table_format(self):
        """
        Check whether table is long (keys in one column, values in the other)
        or wide (keys in one row, values in the other).
        """
        table = self.data['table']
        if any([re.search(u'\xa0', td.text)
                for tr in table.findAll('tr')
                for td in tr.findAll('td')]):
            logger.debug("non-breaking space found in table; long format")
            return 'long'
        else:
            logger.debug("no non-breaking space found in table; wide format")
            return 'wide'

    def _parse_long(self):
        """
        Parse long-formatted table to dictionary.
        """
        table = self.data['table']

        metrics = {}
        for tr in table.findAll('tr'):
            for td in tr.findAll('td'):
                if re.search('^(\w+_*)+$', td.text):
                    td_key = td.text.replace('\n', '')
                    logger.debug("found long metrics field '{}'".format(td_key))

                    td_val = td.next_sibling.string.replace(u'\xa0', u'')
                    td_val = td_val.replace('\n', '')
                    logger.debug("with corresponding long value '{}'".format(td_val))

                    if len(td_val) and not re.search(r'[^\d.]+',
                                                     td_val.lower()):
                        td_val = float(td_val)
                    # The following is a bug fix for the fact that
                    # wide tables don't have values for some keys at the end of the row (LIBRARY, GROUP, etc.)
                    # Don't write metrics that have empty string keys in long tables.
                    # The goal is to match metric keys from wide and long tables.
                    # (Long picard-rnaseq tables are an aberration when the library is of very poor quality) 
                    if td_val != '':
                        metrics[td_key] = td_val
        logger.debug("parsed long metrics table: {}".format(metrics))
        return metrics

    def _parse_wide(self):
        """
        Parse wide-formatted table to dictionary.
        """
        table = self.data['table']
        metrics = {}
        for tr in table.findAll('tr'):
            if re.search(u'\xa0', tr.text):
                return {}
            for td in tr.findAll('td'):
                if re.search('^[A-Z]+', td.text):
                    td_keys = td.text.split('\t')
                    logger.debug("found wide metrics fields: {}".format(td_keys))

                    td_vals = tr.next_sibling.next_sibling.text.split('\t')
                    logger.debug("found corresponding wide values: {}"
                                 .format(td_vals))

                    metrics_tmp = dict(zip(td_keys, td_vals))
                    metrics.update({k: float(v) if not re.search(r'[^\d.]+', v)
                                    else v
                                    for k, v in metrics_tmp.items()})
        logger.debug("parsed wide metrics table: {}".format(metrics))
        return metrics

    def parse(self):
        """
        Parse metrics table and return dictionary.
        """
        self._read_file()
        self._get_table()
        table_format = self._check_table_format()
        if table_format == 'long':
            return self._parse_long()
        else:
            return self._parse_wide()
