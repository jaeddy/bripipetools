import os
import sys

import pytest
import mock

# TODO: might be worthwhile to test import, since I'm still changing module
# names occasionally
from bripipetools.globusgalaxy import submission

@pytest.fixture(scope="class")
def globus_submit_manager():
    flowcell_dir = './tests/test-data/genomics/Illumina/150615_D00565_0087_AC6VG0ANXX'
    workflow_dir = './tests/test-data/genomics/galaxy_workflows'
    endpoint = 'jeddy#srvgridftp01'
    return submission.GlobusSubmitManager(flowcell_dir, workflow_dir, endpoint)

class TestGlobusSubmitManager:
    def test_init(self):
        assert(globus_submit_manager())
        assert('flowcell_dir' in dir(globus_submit_manager()))
        assert('workflow_dir' in dir(globus_submit_manager()))
        assert('endpoint' in dir(globus_submit_manager()))


from bripipetools.globusgalaxy import postprocessing

@pytest.fixture(scope="class")
def globus_output_manager(batch_list='foo,bar'):
    flowcell_dir = './tests/test-data/genomics/Illumina/150615_D00565_0087_AC6VG0ANXX'
    return postprocessing.GlobusOutputManager(flowcell_dir, batch_list)

class TestGlobusOutputManager:
    def test_init_w_batch_list(self):
        assert(globus_output_manager())
        assert('flowcell_dir' in dir(globus_output_manager()))
        assert('batch_submit_dir' in dir(globus_output_manager()))
        assert(globus_output_manager().batch_list ==
               [('./tests/test-data/genomics/Illumina/'
                '150615_D00565_0087_AC6VG0ANXX/globus_batch_submission/foo'),
                ('./tests/test-data/genomics/Illumina/'
                 '150615_D00565_0087_AC6VG0ANXX/globus_batch_submission/bar')])

    def test_select_batch_prompt(self, capsys):
        with mock.patch('__builtin__.raw_input', return_value=""):
            globus_output_manager()._select_batch_prompt()
            out, err = capsys.readouterr()
            assert(err == "Select batch to process: \n")

    def test_select_batch_date_prompt(self, capsys):
        with mock.patch('__builtin__.raw_input', return_value=""):
            globus_output_manager()._select_batch_date_prompt()
            out, err = capsys.readouterr()
            assert(err == "Select date of batch(es) to process: \n")

    def test_select_batches_0(self):
        with mock.patch('__builtin__.raw_input', return_value="0"):
            assert(globus_output_manager()._select_batches() ==
                   [('160216_P109-1_P14-12_C6VG0ANXX_'
                     'optimized_truseq_unstrand_sr_grch38_v0.1_complete.txt')])

    def test_select_date_batches_1(self):
        with mock.patch('__builtin__.raw_input', return_value="1"):
            assert(globus_output_manager()._select_date_batches() ==
                   [('160411_P43-12_C6VG0ANXX_'
                     'optimized_nextera_sr_grch38_v0.1_complete.txt')])

    def test_get_batch_file_path_dummy_file(self):
        assert(globus_output_manager()._get_batch_file_path('dummy.txt') ==
               ('./tests/test-data/genomics/Illumina/'
                '150615_D00565_0087_AC6VG0ANXX/globus_batch_submission/'
                'dummy.txt'))

    def test_get_select_func_each(self):
        assert(globus_output_manager()._get_select_func('each').__name__ ==
               '_select_batches')

    def test_get_select_func_date(self):
        assert(globus_output_manager()._get_select_func('date').__name__ ==
               '_select_date_batches')

    def test_init_no_batch_list(self):
        with mock.patch('__builtin__.raw_input', return_value="0"):
            assert(globus_output_manager(batch_list=None).batch_list ==
                   [('./tests/test-data/genomics/Illumina/'
                     '150615_D00565_0087_AC6VG0ANXX/globus_batch_submission/'
                     '160216_P109-1_P14-12_C6VG0ANXX_'
                     'optimized_truseq_unstrand_sr_grch38_v0.1_complete.txt')])

    def test_curate_batches_dummy(self):
        with pytest.raises(IOError):
            assert(globus_output_manager().curate_batches())
