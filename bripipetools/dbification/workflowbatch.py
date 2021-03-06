"""
Class for importing data from a processing batch into databases as new objects.
Supports both research database ("genomics...") and GenLIMS collections.
"""
import logging

from .. import parsing
from .. import database
from .. import annotation

logger = logging.getLogger(__name__)


class WorkflowBatchImporter(object):
    """
    Collects WorkflowBatch and ProcessedLibrary objects from a processing
    batch, converts to documents, inserts into database.
    """
    def __init__(self, path, db, run_opts):
        logger.debug("creating `ProcessingImporter` instance")
        logger.debug("...with arguments (path: '{}', db: '{}')"
                     .format(path, db.name))
        self.path = path
        self.db = db
        self.run_opts = run_opts

    def _collect_workflowbatch(self):
        """
        Collect WorkflowBatch object for flowcell run.
        """
        path_items = parsing.parse_batch_file_path(self.path)
        logger.info("collecting info for workflow batch file '{}'"
                    .format(path_items['workflowbatch_filename']))

        return annotation.WorkflowBatchAnnotator(
            workflowbatch_file=self.path,
            pipeline_root=path_items['pipeline_root'],
            db=self.db,
            run_opts = self.run_opts
            ).get_workflow_batch()

    def _collect_processedlibraries(self):
        """
        Collect list of ProcessedLibrary objects for flowcell run.
        """
        path_items = parsing.parse_batch_file_path(self.path)
        logger.info("collecting sequenced libraries for workflow batch '{}'"
                    .format(path_items['workflowbatch_filename']))

        return annotation.WorkflowBatchAnnotator(
            workflowbatch_file=self.path,
            pipeline_root=path_items['pipeline_root'],
            db=self.db,
            run_opts=self.run_opts
            ).get_processed_libraries(qc=False)
        
    def _insert_genomicsWorkflowbatch(self):
        """
        Convert WorkflowBatch object and insert into database.
        """
        workflowbatch = self._collect_workflowbatch()
        logger.debug("inserting workflow batch '{}'".format(workflowbatch))
        database.put_genomicsWorkflowbatches(self.db, workflowbatch.to_json())
            
    def _insert_genomicsProcessedlibraries(self):
        """
        Convert ProcessedLibrary objects and insert into database.
        """
        processedlibraries = self._collect_processedlibraries()
        for pl in processedlibraries:
            logger.debug("inserting processed library '{}'".format(pl))
            database.put_genomicsSamples(self.db, pl.to_json())

    def insert(self, collection='all'):
        """
        Insert documents into databases. Note that ResearchDB collections
        are prepended by "genomics" to indicate the data origin.
        """
        # Data for ResearchDB
        if collection in ['all', 'genomicsSamples']:
            logger.info(("Inserting processed libraries for workflow batch "
                         "'{}' into '{}'").format(self.path, self.db.name))
            self._insert_genomicsProcessedlibraries()
        if collection in ['all', 'genomicsWorkflowbatches']:
            logger.info("Inserting workflow batch '{}' into '{}'"
                        .format(self.path, self.db.name))
            self._insert_genomicsWorkflowbatch()
