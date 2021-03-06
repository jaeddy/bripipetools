"""
Class for reading and parsing htseq files.
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class HtseqCountsFile(object):
    """
    Parser to read tables of counts generated by the htseq-count tool,
    stored in a tab-delimited text file.
    """
    def __init__(self, path):
        self.path = path
        self.data = {}

    def _read_file(self):
        """
        Read file into Pandas data frame.
        """
        logger.debug("reading file '{}' to data frame".format(self.path))
        self.data['table'] = pd.read_table(self.path,
                                           names=['geneName', 'count'])

    def parse(self):
        """
        Parse counts file and return data frame.
        """
        self._read_file()
        return self.data['table']
