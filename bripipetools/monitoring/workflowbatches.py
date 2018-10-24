"""
Monitor the outputs of a workflow processing batch.
"""
import logging
import os
import re

from .. import util
from .. import io

logger = logging.getLogger(__name__)


class WorkflowBatchMonitor(object):
    def __init__(self, workflowbatch_file, pipeline_root):
        """
        Controls operations (identification, annotation, etc.) for the
        set of outputs generated by a batch processing job in Globus
        Galaxy.

        :type workflowbatch_file: str
        :param workflowbatch_file: File path of the submitted workflow
            batch file.
        :type pipeline_root: str
        :param pipeline_root: Path to the root directory for processing
        """
        logger.debug("creating `WorkflowBatchMonitor` instance for '{}'"
                     .format(workflowbatch_file))
        self.workflowbatch_file = workflowbatch_file
        self.workflowbatch_data = io.WorkflowBatchFile(
            self.workflowbatch_file,
            state='submit'
        ).parse()
        self.pipeline_root = pipeline_root

    def _get_outputs(self):
        """
        Collect all output files for the workflow batch, grouped by
        sample.

        :return: A list of dicts, one for each sample in the
            workflow batch, where key-value pairs in the dict describe
            the tag/label and path to each output file for the sample.
        """
        return [{p['tag']: p['value'] for p in sample_params
                 if p['type'] == 'output' and p['name'] == 'to_path'}
                for sample_params in self.workflowbatch_data['samples']]

    def _clean_output_paths(self, outputs):
        """
        Replaces ambiguous file path roots with current system root.

        :type outputs: list
        :param outputs: A list of dicts, one for each sample in the
            workflow batch, where key-value pairs in the dict describe
            the tag/label and path to each output file for the sample.

        :rtype: list
        :return: A list of dicts, with output file paths updated to
            use the current system root for the 'genomics' server.
        """
        return [{out_tag: util.swap_root(out_path,
                                         'pipeline', self.pipeline_root)
                 for out_tag, out_path in sample_outputs.items()}
                for sample_outputs in outputs]

    def check_outputs(self):
        """
        Check whether all expected output files are present for each
        sample in the batch.

        :rtype: dict
        :return: A dict, where for each sample, output files are
            flagged as ok, missing, or empty.
        """
        outputs = self._clean_output_paths(self._get_outputs())
        logger.debug("checking status for the following outputs: {}"
                     .format(outputs))

        output_status = {}
        for sample_outputs in outputs:
            for out_tag, out_path in sample_outputs.items():
                logger.debug("checking status for output '{}' at path '{}'"
                             .format(out_tag, out_path))
                path_exists = os.path.exists(out_path)
                path_size = os.stat(out_path).st_size if path_exists else 0
                path_status = 'empty' if path_size == 0 else 'ok'
                path_status = 'missing' if not path_exists else path_status
                output_status[out_path] = {
                    'exists': path_exists,
                    'size': path_size,
                    'status': path_status
                }
                logger.debug("status info for output at path '{}' is {}"
                             .format(out_path, output_status[out_path]))

        return output_status
        
    def check_project_outputs(self, project_id):
        """
        Check whether all expected output files are present for each
        sample in the batch that is part of the indicated project.

        :rtype: dict
        :return: A dict, where for each sample, output files are
            flagged as ok, missing, or empty.
        """
        all_outputs = self._clean_output_paths(self._get_outputs())
        logger.debug("checking status for the following outputs: {}"
                     .format(all_outputs))
                     
        project_outputs = []
        for sample_output in all_outputs:
            project_output = {k:v for k,v 
                              in sample_output.items() 
                              if project_id in v}
            if project_output:
                project_outputs.append(project_output)

        output_status = {}

        for sample_outputs in project_outputs:
            for out_tag, out_path in sample_outputs.items():
                logger.debug("checking status for output '{}' at path '{}'"
                             .format(out_tag, out_path))
                path_exists = os.path.exists(out_path)
                path_size = os.stat(out_path).st_size if path_exists else 0
                path_status = 'empty' if path_size == 0 else 'ok'
                path_status = 'missing' if not path_exists else path_status
                output_status[out_path] = {
                    'exists': path_exists,
                    'size': path_size,
                    'status': path_status
                }
                logger.debug("status info for output at path '{}' is {}"
                             .format(out_path, output_status[out_path]))

        return output_status


