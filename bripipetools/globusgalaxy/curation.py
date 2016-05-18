import os

from bripipetools.util import strings
from bripipetools.util import files
from bripipetools.io import labels
from bripipetools.io.parsers import WorkflowParser
from bripipetools.globusgalaxy.annotation import GlobusOutputAnnotator
# from bripipetools.globusgalaxy.fileops import FileMunger

class BatchCurator(object):
    def __init__(self, batch_submit_file, flowcell_dir=None):
        """
        Controls operations (identification, annotation, etc.) for the set of
        outputs generated by a batch processing job in Globus Galaxy.

        :type batch_submit_file: str
        :param batch_submit_file: File path of the batch submit file.

        :type flowcell_dir: str
        :param flowcell_dir: Path to flowcell folder where outputs are to be
            stored; if not specified, assumed to be one level up from folder
            containing ``batch_submit_file``.
        """
        self.submit_file = batch_submit_file
        if flowcell_dir is None:
            self.fc_dir = os.path.dirname(os.path.dirname(self.submit_file))
        else:
            self.fc_dir = flowcell_dir
        self._load_output_map()
        self._clean_output_paths()

    def _load_output_map(self):
        """
        Parse the batch submit file to obtain and store the mapping between
        samples and their expected output files.
        """
        wp = WorkflowParser(self.submit_file)
        self.workflow_name = wp.get_workflow_name()
        self.sample_output_map = wp.get_batch_outputs()

    def _clean_output_paths(self):
        """
        Replaces ambigious file path roots with current system root.
        """
        sample_output_map = self.sample_output_map
        current_root = files.locate_root_folder('genomics')

        for (sample, sample_files) in sample_output_map.items():
            for file_id in sample_files:
                sample_files[file_id] = files.swap_root(sample_files[file_id],
                                                        'genomics',
                                                        current_root)

        self.sample_output_map = sample_output_map

    def _match_sample_project(self, sample_output_map, sample):
        """
        For a selected sample, check the location of the workflow log output
        file to determine the correct project folder.

        :type sample_output_map: dict
        :param sample_output_map: Dict mapping samples to expected output
            files in the flowcell folder.

        :type sample: str
        :param sample: Name of current sample (i.e., a key in the
            sample-to-output mapping dictionary)

        :rtype: str
        :return: File path of project folder for the current sample.
        """
        log_file = sample_output_map[sample].get('workflow_log_txt')
        project_folder = strings.matchdefault('Project_[^/]*', log_file)
        return os.path.join(self.fc_dir, project_folder)

    def check_outputs(self):
        """
        Check whether all expected output files are present for each sample in
        the batch.

        :rtype: dict
        :return: A dict, where for each ``sample``, output files are flagged as
            ok, missing, or empty.
        """
        sample_output_map = self.sample_output_map

        output_status_dict = {}
        for sample in sample_output_map:
            output_list = [{'path': v, 'type': k}
                           for (k, v) in sample_output_map[sample].items()]

            for f in output_list:
                f['exists'] = os.path.exists(f['path'])
                f['size'] = os.stat(f['path']).st_size if f['exists'] else 0
                if not f['exists']:
                    f['status'] = 'missing'
                else:
                    f['status'] = 'empty' if f['size'] == 0 else 'ok'
            output_status_dict[sample] = output_list

        return output_status_dict

    def report_problem_outputs(self):
        """
        Return non-zero status and display missing/empty files (if any exist).
        """
        # TODO: turn this into an actual error message / raise exception
        output_status_dict = self.check_outputs()

        problem_outputs = [(sample, output['path'])
                           for sample in output_status_dict
                           for output in output_status_dict[sample]
                           if output['status'] != 'ok']

        if len(problem_outputs):
            print(problem_outputs)
            return 1
        else:
            return 0

    def curate_outputs(self):
        """
        For each sample in the processed batch, identify and classify each
        output file present in the flowcell folder.

        :rtype: dict
        :return: A dict, where for each ``sample``, output files are detailed
            and grouped by source.
        """
        workflow_name = self.workflow_name
        sample_output_map = self.sample_output_map

        print('\nWorkflow: {}'.format(workflow_name))
        sample_output_info = {}
        for idx, sample in enumerate(sample_output_map):
            project_dir = self._match_sample_project(sample_output_map, sample)
            # TODO: might want to store project folder somewhere
            project_id, subproject_id = labels.get_project_id(project_dir)

            print('>> Compiling ouputs for {} [P{}-{}] ({} of {})\n'
                  .format(sample, project_id, subproject_id,
                          idx + 1, len(sample_output_map)))

            goa = GlobusOutputAnnotator(sample_output_map, sample)
            sample_output_info[sample] = goa.get_output_info()
        return sample_output_info

    def organize_files(self, target_dir, sample_output_info=None):
        """
        For the outputs identified, rename and reorganize files as needed.

        :type target_dir: str
        :param target_dir: path to folder where final output files are to be
            saved
        """
        if sample_output_info is None:
            sample_output_info = self.curate_outputs()

        for sample, packet in sample_output_info.items():
            fpm = fileops.FilePacketManager(packet, sample, '.')

        # for source in sample_output_info:
        #     fm = FileMunger(self, target_dir, source)
        #     fm.go()
        # # TODO: return something...
