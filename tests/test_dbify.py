import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import os

import pytest
import mongomock
import pymongo

from bripipetools import model as docs
from bripipetools import dbify

@pytest.fixture(scope='class')
def mock_genomics_server(request):
    logger.info(("[setup] mock 'genomics' server, connect "
                 "to mock 'genomics' server"))
    run_id = '150615_D00565_0087_AC6VG0ANXX'
    mock_genomics_root = './tests/test-data/'
    mock_genomics_path = os.path.join(mock_genomics_root, 'genomics')
    mock_flowcell_path = os.path.join(mock_genomics_path, 'Illumina', run_id)
    mock_unaligned_path = os.path.join(mock_flowcell_path, 'Unaligned')
    mock_workflow_batch_file = os.path.join(
        mock_flowcell_path, 'globus_batch_submission',
        ("160412_P109-1_P14-12_C6VG0ANXX_"
         "optimized_truseq_unstrand_sr_grch38_v0.1_complete.txt")
    )

    data = {'run_id': run_id,
            'genomics_root': mock_genomics_root,
            'genomics_path': mock_genomics_path,
            'flowcell_path': mock_flowcell_path,
            'unaligned_path': mock_unaligned_path,
            'project_p14_12': 'P14-12-23221204',
            'project_p109_1': 'P109-1-21113094',
            'lib7293': 'lib7293-25920016',
            'lib7293_fastq': 'MXU01-CO072_S1_L001_R1_001.fastq.gz',
            'workflowbatch_file': mock_workflow_batch_file,
            'batch_name': '160412_P109-1_P14-12_C6VG0ANXX'}
    def fin():
        logger.info(("[teardown] mock 'genomics' server, disconnect "
                     "from mock 'genomics' server"))
    request.addfinalizer(fin)
    return data

@pytest.fixture(scope='class')
def mock_db(request):
    logger.info(("[setup] mock 'tg3' database, connect "
                 "to mock 'tg3' Mongo database"))
    db = mongomock.MongoClient().db

    def fin():
        logger.info(("[teardown] mock 'tg3' database, disconnect "
                     "from mock 'tg3' Mongo database"))
    request.addfinalizer(fin)
    return db


@pytest.mark.usefixtures('mock_genomics_server', 'mock_db')
class TestSequencingImporter:
    @pytest.fixture(scope='class')
    def importer(self, request, mock_genomics_server, mock_db):
        logger.info("[setup] SequencingImporter test instance")

        # GIVEN a SequencingImporter with mock 'genomics' server path to
        # flowcell run directory and mock database connection
        sequencingimporter = dbify.SequencingImporter(
            path=mock_genomics_server['flowcell_path'],
            db=mock_db
        )
        def fin():
            logger.info("[teardown] SequencingImporter mock instance")
        request.addfinalizer(fin)
        return sequencingimporter

    def test_parse_flowcell_path(self, importer, mock_genomics_server):
        logger.info("test `_get_genomics_root()`")

        # WHEN the path argument is parsed to find the 'genomics' root
        # and flowcell run ID
        path_items = importer._parse_flowcell_path()

        # THEN the 'genomics' root and run ID should match the mock server
        assert(path_items['genomics_root']
               == mock_genomics_server['genomics_root'])
        assert(path_items['run_id']
               == mock_genomics_server['run_id'])

    def test_collect_flowcellrun(self, importer):
        logger.info("test `_collect_flowcellrun()`")

        # WHEN collecting FlowcellRun object for flowcell run
        flowcellrun = importer._collect_flowcellrun()

        # THEN should return object of correct type
        assert(type(flowcellrun) == docs.FlowcellRun)

    def test_collect_sequencedlibraries(self, importer):
        logger.info("test `_collect_sequencedlibraries()`")

        # WHEN collecting list of SequencedLibrary objects for flowcell run
        sequencedlibraries = importer._collect_sequencedlibraries()

        # THEN should return 31 total objects of correct type
        assert(len(sequencedlibraries) == 31)
        assert(all([type(sl) == docs.SequencedLibrary
                    for sl in sequencedlibraries]))

    def test_insert_flowcellrun(self, importer, mock_db):
        logger.info("test `_insert_flowcellrun()`")

        # WHEN flowcell run is inserted into database
        importer._insert_flowcellrun()

        # THEN documents should be present in the runs collection
        assert(len(list(mock_db.runs.find({'type': 'flowcell'})))
               == 1)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop runs collection from mock database"))
        mock_db.runs.drop()

    def test_insert_sequencedlibraries(self, importer, mock_db):
        logger.info("test `_insert_sequencedlibraries()`")

        # WHEN sequenced libraries are inserted into database
        importer._insert_sequencedlibraries()

        # THEN documents should be present in the samples collection
        assert(len(list(mock_db.samples.find({'type': 'sequenced library'})))
               == 31)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()

    def test_insert_all(self, importer, mock_db):
        logger.info("test `_insert()` for all collections")

        # WHEN inserting with collection argument set to 'all' (default)
        importer.insert()

        # THEN documents should be present in both runs and samples collections
        assert(len(list(mock_db.runs.find({'type': 'flowcell'})))
               == 1)
        assert(len(list(mock_db.samples.find({'type': 'sequenced library'})))
               == 31)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop runs collection from mock database"))
        mock_db.runs.drop()
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()

    def test_insert_runs(self, importer, mock_db):
        logger.info("test `_insert()` for runs only")

        # WHEN inserting with collection argument set to 'runs'
        importer.insert(collection='runs')

        # THEN documents should be present in only runs collections
        assert(len(list(mock_db.runs.find({'type': 'flowcell'})))
               == 1)
        assert(len(list(mock_db.samples.find({'type': 'sequenced library'})))
               == 0)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop runs collection from mock database"))
        mock_db.runs.drop()
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()

    def test_insert_samples(self, importer, mock_db):
        logger.info("test `_insert()` for samples only")

        # WHEN inserting with collection argument set to 'samples'
        importer.insert(collection='samples')

        # THEN documents should be present in only runs collections
        assert(len(list(mock_db.runs.find({'type': 'flowcell'})))
               == 0)
        assert(len(list(mock_db.samples.find({'type': 'sequenced library'})))
               == 31)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop runs collection from mock database"))
        mock_db.runs.drop()
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()


@pytest.mark.usefixtures('mock_genomics_server', 'mock_db')
class TestProcessingImporter:
    @pytest.fixture(scope='class')
    def importer(self, request, mock_genomics_server, mock_db):
        logger.info("[setup] ProcessingImporter test instance")

        # GIVEN a ProcessingImporter with mock 'genomics' server path to
        # workflow batch file and mock database connection
        processingimporter = dbify.ProcessingImporter(
            path=mock_genomics_server['workflowbatch_file'],
            db=mock_db
        )
        def fin():
            logger.info("[teardown] ProcessingImporter mock instance")
        request.addfinalizer(fin)
        return processingimporter

    def test_parse_batch_file_path(self, importer, mock_genomics_server):
        logger.info("test `_get_genomics_root()`")

        # WHEN the path argument is parsed to find the 'genomics' root
        # and workflow batch file name
        path_items = importer._parse_batch_file_path()

        # THEN the 'genomics' root and run ID should match the mock server
        assert(path_items['genomics_root']
               == mock_genomics_server['genomics_root'])
        assert(path_items['workflowbatch_filename']
               == os.path.basename(mock_genomics_server['workflowbatch_file']))

    def test_collect_workflowbatch(self, importer):
        logger.info("test `_collect_workflowbatch()`")

        # WHEN collecting WorkflowBatch object for processing batch
        workflowbatch = importer._collect_workflowbatch()

        # THEN should return object of correct type
        assert(type(workflowbatch) == docs.GalaxyWorkflowBatch)

    def test_collect_processedlibraries(self, importer):
        logger.info("test `_collect_processedlibraries()`")

        # WHEN collecting list of ProcessedLibrary objects for workflow batch
        processedlibraries = importer._collect_processedlibraries()

        # THEN should return 2 total objects of correct type
        assert(len(processedlibraries) == 2)
        assert(all([type(pl) == docs.ProcessedLibrary
                    for pl in processedlibraries]))

    def test_insert_workflowbatch(self, importer, mock_db):
        logger.info("test `_insert_workflowbatch()`")

        # WHEN workflow batch is inserted into database
        importer._insert_workflowbatch()

        # THEN documents should be present in the workflowbatches collection
        assert(len(list(mock_db.workflowbatches.find(
               {'type': 'Galaxy workflow batch'})))
               == 1)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop workflowbatches collection from mock database"))
        mock_db.workflowbatches.drop()

    def test_insert_processedlibraries(self, importer, mock_db):
        logger.info("test `_insert_processedlibraries()`")

        # WHEN processed libraries are inserted into database
        importer._insert_processedlibraries()

        # THEN documents should be present in the samples collection
        assert(len(list(mock_db.samples.find({'type': 'processed library'})))
               == 2)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()

    def test_insert_all(self, importer, mock_db):
        logger.info("test `_insert()` for all collections")

        # WHEN inserting with collection argument set to 'all' (default)
        importer.insert()

        # THEN documents should be present in both workflowbatches and
        # samples collections
        assert(len(list(mock_db.workflowbatches.find(
               {'type': 'Galaxy workflow batch'})))
               == 1)
        assert(len(list(mock_db.samples.find({'type': 'processed library'})))
               == 2)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop workflowbatches collection from mock database"))
        mock_db.workflowbatches.drop()
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()

    def test_insert_workflowbatches(self, importer, mock_db):
        logger.info("test `_insert()` for workflowbatches only")

        # WHEN inserting with collection argument set to 'workflowbatches'
        importer.insert(collection='workflowbatches')

        # THEN documents should be present in only workflowbatches collections
        assert(len(list(mock_db.workflowbatches.find(
               {'type': 'Galaxy workflow batch'})))
               == 1)
        assert(len(list(mock_db.samples.find({'type': 'processed library'})))
               == 0)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop workflowbatches collection from mock database"))
        mock_db.workflowbatches.drop()
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()

    def test_insert_samples(self, importer, mock_db):
        logger.info("test `_insert()` for samples only")

        # WHEN inserting with collection argument set to 'samples'
        importer.insert(collection='samples')

        # THEN documents should be present in only runs collections
        assert(len(list(mock_db.workflowbatches.find(
               {'type': 'Galaxy workflow batch'})))
               == 0)
        assert(len(list(mock_db.samples.find({'type': 'processed library'})))
               == 2)
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop workflowbatches collection from mock database"))
        mock_db.workflowbatches.drop()
        logger.info(("[semi-teardown] mock 'tg3' database, "
                     "drop samples collection from mock database"))
        mock_db.samples.drop()


@pytest.mark.usefixtures('mock_genomics_server', 'mock_db')
class TestImportManagerWithFlowcellPath:
    @pytest.fixture(scope='class')
    def manager(self, request, mock_genomics_server, mock_db):
        logger.info("[setup] ImportManager test instance")

        # GIVEN a ImportManager with mock database connection and path
        # to a flowcell directory
        importmanager = dbify.ImportManager(
            path=mock_genomics_server['flowcell_path'],
            db=mock_db
        )
        def fin():
            logger.info("[teardown] ImportManager mock instance")
        request.addfinalizer(fin)
        return importmanager

    def test_sniff_path_flowcell_path(self, manager, mock_genomics_server):
        logger.info("test `_sniff_path()` for flowcell path")

        # WHEN a flowcell path is checked to determine type
        path_type = manager._sniff_path(mock_genomics_server['flowcell_path'])

        # THEN path type should be 'flowcell_path'
        assert(path_type == 'flowcell_path')

    def test_sniff_path_workflowbatch_file(self, manager, mock_genomics_server):
        logger.info("test `_sniff_path()` for workflow batch file")

        # WHEN a flowcell path is checked to determine type
        path_type = manager._sniff_path(
            mock_genomics_server['workflowbatch_file'])

        # THEN path type should be 'flowcell_path'
        assert(path_type == 'workflowbatch_file')

    def test_init_importer(self, manager):
        logger.info("test `_init_importer()`")

        # WHEN importer is selected
        manager._init_importer()
        importer = manager.importer

        # THEN should be of type SequencingImporter
        assert(type(importer) == dbify.SequencingImporter)

    def test_run(self, manager, mock_db):
        logger.info("test `run()`")

        # WHEN using run to execute the importer insert method
        manager.run()

        # THEN documents should be present in both runs and samples collections
        assert(len(list(mock_db.runs.find({'type': 'flowcell'})))
               == 1)
        assert(len(list(mock_db.samples.find({'type': 'sequenced library'})))
               == 31)


@pytest.mark.usefixtures('mock_genomics_server', 'mock_db')
class TestImportManagerWithWorkflowBatchFile:
    @pytest.fixture(scope='class')
    def manager(self, request, mock_genomics_server, mock_db):
        logger.info("[setup] ImportManager test instance")

        # GIVEN a ImportManager with mock database connection and path
        # to a workflow batch file
        importmanager = dbify.ImportManager(
            path=mock_genomics_server['workflowbatch_file'],
            db=mock_db
        )
        def fin():
            logger.info("[teardown] ImportManager mock instance")
        request.addfinalizer(fin)
        return importmanager

    def test_sniff_path_flowcell_path(self, manager, mock_genomics_server):
        logger.info("test `_sniff_path()` for flowcell path")

        # WHEN a flowcell path is checked to determine type
        path_type = manager._sniff_path(mock_genomics_server['flowcell_path'])

        # THEN path type should be 'flowcell_path'
        assert(path_type == 'flowcell_path')

    def test_sniff_path_workflowbatch_file(self, manager, mock_genomics_server):
        logger.info("test `_sniff_path()` for workflow batch file")

        # WHEN a flowcell path is checked to determine type
        path_type = manager._sniff_path(
            mock_genomics_server['workflowbatch_file'])

        # THEN path type should be 'flowcell_path'
        assert(path_type == 'workflowbatch_file')

    def test_init_importer(self, manager):
        logger.info("test `_init_importer()`")

        # WHEN importer is selected
        manager._init_importer()
        importer = manager.importer

        # THEN should be of type SequencingImporter
        assert(type(importer) == dbify.ProcessingImporter)

    def test_run(self, manager, mock_db):
        logger.info("test `run()`")

        # WHEN using run to execute the importer insert method
        manager.run()

        # THEN documents should be present in both workflowbatches and
        # samples collections
        assert(len(list(mock_db.workflowbatches.find(
               {'type': 'Galaxy workflow batch'})))
               == 1)
        assert(len(list(mock_db.samples.find({'type': 'processed library'})))
               == 2)