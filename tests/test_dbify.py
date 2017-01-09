import logging
import os

import pytest
import mongomock

from bripipetools import model as docs
from bripipetools import dbify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def mock_db():
    # GIVEN a mocked version of the TG3 Mongo database
    logger.info(("[setup] mock database, connect "
                 "to mock Mongo database"))

    yield mongomock.MongoClient().db
    logger.debug(("[teardown] mock database, disconnect "
                  "from mock Mongo database"))


class TestFlowcellRunImporter:
    """

    """
    def test_parse_flowcell_path(self, mock_db):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist
        mock_root = '/mnt/'
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = '{}genomics/Illumina/{}'.format(mock_root, mock_id)

        # AND an importer object is created for the path
        importer = dbify.FlowcellRunImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN the path argument is parsed to find the 'genomics' root
        # and flowcell run ID
        test_items = importer._parse_flowcell_path()

        # THEN the 'genomics' root and run ID should match the mock server
        assert (test_items['genomics_root'] == mock_root)
        assert (test_items['run_id'] == mock_id)

    def test_collect_flowcellrun(self, mock_db):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist (note: behavior of of the associated
        # FlowcellRunAnnotator class when collecting data about a new or
        # previously imported flowcell run is assumed to be tested in the
        # `test_annotation` module)
        mock_root = '/mnt/'
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = '{}genomics/Illumina/{}'.format(mock_root, mock_id)

        # AND an importer object is created for the path
        importer = dbify.FlowcellRunImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN collecting model object for flowcell run
        test_object = importer._collect_flowcellrun()

        # THEN should return object of correct type
        assert (type(test_object) == docs.FlowcellRun)

    def test_collect_sequenced_libraries(self, mock_db, tmpdir):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = tmpdir.mkdir('genomics').mkdir('Illumina').mkdir(mock_id)

        # AND an unaligned folder, which includes multiple project folders,
        # each with multiple folders for sequenced libraries
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_libs = {0: ['lib1111-11111111', 'lib2222-22222222'],
                     1: ['lib3333-33333333', 'lib4444-44444444']}
        unalignedpath = mock_path.mkdir('Unaligned')
        for idx, p in enumerate(mock_projects):
            projpath = unalignedpath.mkdir(p)
            for l in mock_libs[idx]:
                projpath.mkdir(l)

        # AND an importer object is created for the path
        importer = dbify.FlowcellRunImporter(
            path=str(mock_path),
            db=mock_db
        )

        # WHEN collecting model objects for sequenced libraries
        test_objects = importer._collect_sequencedlibraries()

        # THEN should return object of correct type
        assert (all(type(sl) == docs.SequencedLibrary for sl in test_objects))

    def test_insert_flowcellrun(self, mock_db):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist (note: behavior for inserting or updating
        # documents in the database is assumed to be tested in the
        # `test_genlims` module)
        mock_root = '/mnt/'
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = '{}genomics/Illumina/{}'.format(mock_root, mock_id)

        # AND an importer object is created for the path
        importer = dbify.FlowcellRunImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN flowcell run is inserted into database
        importer._insert_flowcellrun()

        # THEN document should be present in the runs collection
        assert (len(list(mock_db.runs.find({'type': 'flowcell'}))) == 1)

    def test_insert_sequencedlibraries(self, mock_db, tmpdir):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = tmpdir.mkdir('genomics').mkdir('Illumina').mkdir(mock_id)

        # AND an unaligned folder, which includes multiple project folders,
        # each with multiple folders for sequenced libraries
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_libs = {0: ['lib1111-11111111', 'lib2222-22222222'],
                     1: ['lib3333-33333333', 'lib4444-44444444']}
        unalignedpath = mock_path.mkdir('Unaligned')
        for idx, p in enumerate(mock_projects):
            projpath = unalignedpath.mkdir(p)
            for l in mock_libs[idx]:
                projpath.mkdir(l)

        # AND an importer object is created for the path
        importer = dbify.FlowcellRunImporter(
            path=str(mock_path),
            db=mock_db
        )

        # WHEN sequenced libraries are inserted into database
        importer._insert_sequencedlibraries()

        # THEN document should be present in the runs collection
        assert (len(list(mock_db.samples.find({'type': 'sequenced library'})))
                == 4)

    def test_insert(self, mock_db, tmpdir):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = tmpdir.mkdir('genomics').mkdir('Illumina').mkdir(mock_id)

        # AND an unaligned folder, which includes multiple project folders,
        # each with multiple folders for sequenced libraries
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_libs = {0: ['lib1111-11111111', 'lib2222-22222222'],
                     1: ['lib3333-33333333', 'lib4444-44444444']}
        unalignedpath = mock_path.mkdir('Unaligned')
        for idx, p in enumerate(mock_projects):
            projpath = unalignedpath.mkdir(p)
            for l in mock_libs[idx]:
                projpath.mkdir(l)

        # AND an importer object is created for the path
        importer = dbify.FlowcellRunImporter(
            path=str(mock_path),
            db=mock_db
        )

        # WHEN all objects are inserted into database
        importer.insert()

        # THEN documents should be present in the runs collection
        assert (len(list(mock_db.runs.find({'type': 'flowcell'}))) == 1)
        assert (len(list(mock_db.samples.find({'type': 'sequenced library'})))
                == 4)


@pytest.fixture(scope='function')
def mock_batchfile(filename, tmpdir):
    mock_contents = ['###METADATA\n',
                     '#############\n',
                     'Workflow Name\toptimized_workflow_1\n',
                     'Project Name\t161231_P00-00_C00000XX\n',
                     '###TABLE DATA\n',
                     '#############\n',
                     'SampleName\tin_tag##_::_::_::param_name\n',
                     'sample1\tin_value1\n',
                     'sample2\tin_value2\n']
    mock_file = tmpdir.join(filename)
    mock_file.write(''.join(mock_contents))
    return str(mock_file)


class TestWorkflowBatchImporter:
    """

    """
    def test_parse_batch_file_path(self, mock_db, tmpdir):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P00-00_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        importer = dbify.WorkflowBatchImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN the path argument is parsed to find the 'genomics' root
        # and workflow batch file name
        test_items = importer._parse_batch_file_path()

        # THEN the 'genomics' root and run ID should match the mock server
        assert (test_items['genomics_root'].rstrip('/') == str(tmpdir))
        assert (test_items['workflowbatch_filename'] == mock_filename)

    def test_collect_workflowbatch(self, mock_db, tmpdir):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        importer = dbify.WorkflowBatchImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN collecting model object for flowcell run
        test_object = importer._collect_workflowbatch()

        # THEN should return object of correct type
        assert (type(test_object) == docs.GalaxyWorkflowBatch)

    def test_collect_processedlibraries(self, mock_db, tmpdir):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        importer = dbify.WorkflowBatchImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN collecting model object for flowcell run
        test_objects = importer._collect_processedlibraries()

        # THEN should return object of correct type
        assert (all(type(pl) == docs.ProcessedLibrary for pl in test_objects))

    def test_insert_workflowbatch(self, mock_db, tmpdir):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        importer = dbify.WorkflowBatchImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN workflow batch is inserted into database
        importer._insert_workflowbatch()

        # THEN document should be present in the workflowbatches collection
        assert (len(list(mock_db.workflowbatches
                         .find({'type': 'Galaxy workflow batch'})))
                == 1)

    def test_insert_processedlibraries(self, mock_db, tmpdir):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        importer = dbify.WorkflowBatchImporter(
            path=mock_path,
            db=mock_db
        )

        # WHEN flowcell run is inserted into database
        importer._insert_processedlibraries()

        # THEN document should be present in the runs collection
        assert (len(list(mock_db.samples.find({'type': 'processed library'})))
                == 2)

    def test_insert(self, mock_db, tmpdir):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        importer = dbify.WorkflowBatchImporter(
            path=str(mock_path),
            db=mock_db
        )

        # WHEN all objects are inserted into database
        importer.insert()

        # THEN documents should be present in the runs collection
        assert (len(list(mock_db.workflowbatches
                         .find({'type': 'Galaxy workflow batch'})))
                == 1)
        assert (len(list(mock_db.samples.find({'type': 'processed library'})))
                == 2)


class TestImportManager:
    """

    """

    def test_sniff_path_for_flowcell_run(self, mock_db):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = '/mnt/genomics/Illumina/{}'.format(mock_id)

        manager = dbify.ImportManager(
            path=mock_path,
            db=mock_db
        )

        # WHEN path is checked to determine type
        test_type = manager._sniff_path()

        # THEN path type should be 'flowcell_path'
        assert (test_type == 'flowcell_path')

    def test_sniff_path_for_workflow_batch(self, mock_db):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = ('/mnt/genomics/Illumina/{}/globus_batch_submission/{}'
                     .format(mock_id, mock_filename))

        manager = dbify.ImportManager(
            path=mock_path,
            db=mock_db
        )

        # WHEN path is checked to determine type
        test_type = manager._sniff_path()

        # THEN path type should be 'flowcell_path'
        assert (test_type == 'workflowbatch_file')

    def test_init_importer_for_flowcell_run(self, mock_db):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = '/mnt/genomics/Illumina/{}'.format(mock_id)

        manager = dbify.ImportManager(
            path=mock_path,
            db=mock_db
        )

        # WHEN path is checked to determine type
        manager._init_importer()

        # THEN path type should be 'flowcell_path'
        assert (type(manager.importer) == dbify.FlowcellRunImporter)

    def test_init_importer_for_workflow_batch(self, mock_db):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = ('/mnt/genomics/Illumina/{}/globus_batch_submission/{}'
                     .format(mock_id, mock_filename))

        manager = dbify.ImportManager(
            path=mock_path,
            db=mock_db
        )

        # WHEN path is checked to determine type
        manager._init_importer()

        # THEN path type should be 'flowcell_path'
        assert (type(manager.importer) == dbify.WorkflowBatchImporter)

    def test_run_for_flowcell_run(self, mock_db, tmpdir):
        # GIVEN a path to a flowcell run folder and a connection to a
        # database in which a document corresponding to the flowcell run
        # may or may not exist
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = tmpdir.mkdir('genomics').mkdir('Illumina').mkdir(mock_id)

        # AND an unaligned folder, which includes multiple project folders,
        # each with multiple folders for sequenced libraries
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_libs = {0: ['lib1111-11111111', 'lib2222-22222222'],
                     1: ['lib3333-33333333', 'lib4444-44444444']}
        unalignedpath = mock_path.mkdir('Unaligned')
        for idx, p in enumerate(mock_projects):
            projpath = unalignedpath.mkdir(p)
            for l in mock_libs[idx]:
                projpath.mkdir(l)

        # AND an importer object is created for the path
        manager = dbify.ImportManager(
            path=str(mock_path),
            db=mock_db
        )

        # WHEN all objects are inserted into database
        manager.run()

        # THEN documents should be present in the runs collection
        assert (len(list(mock_db.runs.find({'type': 'flowcell'}))) == 1)
        assert (len(list(mock_db.samples.find({'type': 'sequenced library'})))
                == 4)

    def test_run_for_workflow_batch(self, mock_db, tmpdir):
        mock_id = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir.mkdir('genomics').mkdir('Illumina')
                     .mkdir(mock_id).mkdir('globus_batch_submission'))

        mock_filename = '161231_P1-1_P99-99_C00000XX_workflow-name.txt'
        mock_path = mock_batchfile(mock_filename, mock_path)

        # AND an importer object is created for the path
        manager = dbify.ImportManager(
            path=mock_path,
            db=mock_db
        )

        # WHEN all objects are inserted into database
        manager.run()

        # THEN documents should be present in the runs collection
        assert (len(list(mock_db.workflowbatches
                         .find({'type': 'Galaxy workflow batch'})))
                == 1)
        assert (len(list(mock_db.samples.find({'type': 'processed library'})))
                == 2)

# @pytest.mark.usefixtures('mock_genomics_server', 'mock_db')
# class TestImportManagerWithFlowcellPath:
#     @pytest.fixture(
#         scope='class',
#         params=[{'runnum': r, 'batchnum': b}
#                 for r in range(1)
#                 for b in range(2)])
#     def managerdata(self, request, mock_genomics_server, mock_db):
#         # GIVEN a ImportManager with mock database connection and path
#         # to a flowcell directory
#         runs = mock_genomics_server['root']['genomics']['illumina']['runs']
#         rundata = runs[request.param['runnum']]
#         batches = rundata['submitted']['batches']
#         batchdata = batches[request.param['batchnum']]
#
#         logger.info("[setup] ImportManager test instance "
#                     "for run {} and/or workflow batch {}"
#                     .format(rundata['run_id'], batchdata['path']))
#
#         importmanager = dbify.ImportManager(
#             path=rundata['path'],
#             db=mock_db)
#
#         def fin():
#             logger.info("[teardown] ImportManager mock instance")
#         request.addfinalizer(fin)
#         return (importmanager, rundata, batchdata)
#
#     def test_sniff_path_flowcell_path(self, managerdata, mock_genomics_server):
#         # (GIVEN)
#         manager, rundata, _ = managerdata
#
#         logger.info("test `_sniff_path()` for flowcell path")
#
#         # WHEN a flowcell path is checked to determine type
#         path_type = manager._sniff_path(rundata['path'])
#
#         # THEN path type should be 'flowcell_path'
#         assert(path_type == 'flowcell_path')
#
#     def test_sniff_path_workflowbatch_file(self, managerdata,
#                                            mock_genomics_server):
#         # (GIVEN)
#         manager, _, batchdata = managerdata
#
#         logger.info("test `_sniff_path()` for workflow batch file")
#
#         # WHEN a flowcell path is checked to determine type
#         path_type = manager._sniff_path(batchdata['path'])
#
#         # THEN path type should be 'flowcell_path'
#         assert(path_type == 'workflowbatch_file')
#
#     def test_init_importer(self, managerdata):
#         # (GIVEN)
#         manager, _, _ = managerdata
#
#         logger.info("test `_init_importer()`")
#
#         # WHEN importer is selected
#         manager._init_importer()
#         importer = manager.importer
#
#         # THEN should be of type SequencingImporter
#         assert(type(importer) == dbify.SequencingImporter)
#
#     def test_run(self, managerdata, mock_db):
#         # (GIVEN)
#         manager, rundata, _ = managerdata
#
#         logger.info("test `run()`")
#
#         # WHEN using run to execute the importer insert method
#         manager.run()
#
#         # THEN documents should be present in both runs and samples collections
#         assert(len(list(mock_db.runs.find({'type': 'flowcell'})))
#                == 1)
#         assert(len(list(mock_db.samples.find({'type': 'sequenced library'})))
#                == sum(map(lambda x: len(x['samples']),
#                       rundata['unaligned']['projects'])))
#
#         logger.info("[rollback] remove most recently inserted "
#                     "from mock database")
#         mock_db.workflowbatches.drop()
#         mock_db.samples.drop()
#
#
# @pytest.mark.usefixtures('mock_genomics_server', 'mock_db')
# class TestImportManagerWithWorkflowBatchFile:
#     @pytest.fixture(
#         scope='class',
#         params=[{'runnum': r, 'batchnum': b}
#                 for r in range(1)
#                 for b in range(2)])
#     def managerdata(self, request, mock_genomics_server, mock_db):
#         # GIVEN a ImportManager with mock database connection and path
#         # to a flowcell directory
#         runs = mock_genomics_server['root']['genomics']['illumina']['runs']
#         rundata = runs[request.param['runnum']]
#         batches = rundata['submitted']['batches']
#         batchdata = batches[request.param['batchnum']]
#
#         logger.info("[setup] ImportManager test instance "
#                     "for run {} and/or workflow batch {}"
#                     .format(rundata['run_id'], batchdata['path']))
#
#         importmanager = dbify.ImportManager(
#             path=batchdata['path'],
#             db=mock_db)
#
#         def fin():
#             logger.info("[teardown] ImportManager mock instance")
#         request.addfinalizer(fin)
#         return (importmanager, rundata, batchdata)
#
#     def test_sniff_path_flowcell_path(self, managerdata, mock_genomics_server):
#         # (GIVEN)
#         manager, rundata, _ = managerdata
#
#         logger.info("test `_sniff_path()` for flowcell path")
#
#         # WHEN a flowcell path is checked to determine type
#         path_type = manager._sniff_path(rundata['path'])
#
#         # THEN path type should be 'flowcell_path'
#         assert(path_type == 'flowcell_path')
#
#     def test_sniff_path_workflowbatch_file(self, managerdata,
#                                            mock_genomics_server):
#         # (GIVEN)
#         manager, _, batchdata = managerdata
#
#         logger.info("test `_sniff_path()` for workflow batch file")
#
#         # WHEN a flowcell path is checked to determine type
#         path_type = manager._sniff_path(batchdata['path'])
#
#         # THEN path type should be 'flowcell_path'
#         assert(path_type == 'workflowbatch_file')
#
#     def test_init_importer(self, managerdata):
#         # (GIVEN)
#         manager, _, _ = managerdata
#
#         logger.info("test `_init_importer()`")
#
#         # WHEN importer is selected
#         manager._init_importer()
#         importer = manager.importer
#
#         # THEN should be of type SequencingImporter
#         assert(type(importer) == dbify.ProcessingImporter)
#
#     def test_run(self, managerdata, mock_db):
#         # (GIVEN)
#         manager, _, batchdata = managerdata
#
#         logger.info("test `run()`")
#
#         # WHEN using run to execute the importer insert method
#         manager.run()
#
#         # THEN documents should be present in both workflowbatches and
#         # samples collections
#         assert(len(list(mock_db.workflowbatches.find(
#                {'type': 'Galaxy workflow batch'})))
#                == 1)
#         assert(len(list(mock_db.samples.find({'type': 'processed library'})))
#                == batchdata['num_samples'])
#
#         logger.info("[rollback] remove most recently inserted "
#                     "from mock database")
#         mock_db.workflowbatches.drop()
#         mock_db.samples.drop()
