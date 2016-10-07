"""
Class for reading and parsing Tophat Stats metrics files.
"""
import logging
logger = logging.getLogger(__name__)
import re


class HtseqMetricsFile(object):
    """
    Parser to read tables of metrics generated by the htseq-count tool,
    stored in a tab-delimited text file.
    """
    def __init__(self, path):
        self.path = path
        self.data = {}
        self._read_file()

    def _read_file(self):
        """
        Read file into list of raw strings.
        """
        logger.debug("reading file {} as to raw string list".format(self.path))
        with open(self.path) as f:
            self.data['raw'] = f.readlines()

    def _parse_lines(self):
        """
        Get key-value pairs from text lines and return dictionary.
        """
        return {l.strip().split('\t')[0].lstrip('__'): l.strip().split('\t')[1]
                for l in self.data['raw']}

    def parse(self):
        """
        Parse metrics table and return dictionary.
        """
        return self._parse_lines()
