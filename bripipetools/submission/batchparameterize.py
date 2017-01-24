import logging
import os
import re

from .. import util
from .. import parsing

logger = logging.getLogger(__name__)


class BatchParameterizer(object):
    """
    Defines workflow batch parameters for a list of input samples,
    given a list of parsed parameters for a Galaxy workflow.

    :type sample_paths: list
    :param sample_paths: List of paths to sample folders, where each
        folder contains one or more lane-specifc FASTQ file(s).
    :type parameters: list
    :param parameters: List of workflow parameters, parsed from a
        workflow template file, where each parameter is represented
        by a dict with fields ``tag``, ``type``, and ``name``.
    :type target_dir: str
    :param target_dir: Path to folder where outputs are to be saved.
        Subfolders will be created within the ``target_dir`` based
        on output type.
    :type endpoint: str
    :param endpoint: Globus endpoint where input files are accessed
        and output files will be sent (e.g., 'jeddy#srvgridftp01').
    :type build: str
    :param build: ID string of reference genome build to be used
        for processing current set of samples.
    """
    def __init__(self, sample_paths, parameters, endpoint, target_dir,
                 build='GRCh38'):
        logger.debug("creating `BatchParametizer` instance ")
        self.sample_paths = sample_paths
        self.parameters = parameters
        self.endpoint = endpoint
        self.target_dir = target_dir
        self.build = build

    def _get_lane_order(self):
        """
        Return the list of lane numbers (1-8) based on the order in
        which they appear for input FASTQs in the parameter list.
        """
        logger.debug("identifying lane order for input FASTQs")
        return [re.search('[1-8]', p['name']).group()
                for p in self.parameters
                if p['tag'] == 'fastq_in'
                and re.search('from_path', p['name'])]

    def _get_lane_fastq(self, sample_path, lane):
        """
        Retrieve the path for the FASTQ file from the specified lane
        within the sample folder. If no file exists, create and return
        the path of an empty FASTQ file.
        """
        logger.debug("retrieving FASTQ path for sample '{}' and lane {}"
                     .format(sample_path, lane))
        fastq_paths = [os.path.join(sample_path, f)
                       for f in os.listdir(sample_path)
                       if re.search(r'L00{}'.format(lane), f)]
        if len(fastq_paths):
            fastq_path = fastq_paths[0]

        else:
            logger.debug("no FASTQ found for lane {}; creating empty file"
                         .format(lane))
            empty_fastq = 'empty_L00{}.fastq.gz'.format(lane)
            fastq_path = os.path.join(sample_path, empty_fastq)

            if not os.path.exists(fastq_path):
                open(fastq_path, 'a').close()

        return fastq_path

    def _build_reference_path(self, parameter):
        """
        Given a parameter for an input annotation dataset stored in a
        library on Globus Galaxy, return the path to the dataset based
        on the current build and annotation type.
        """
        ref_dict = {
            'GRCh38': {
                'gtf': 'GRCh38/Homo_sapiens.GRCh38.77.gtf',
                'refflat': 'GRCh38/Homo_sapiens.GRCh38.77.refflat.txt',
                'ribosomal_intervals':
                    ('GRCh38/Homo_sapiens.GRCh38.77'
                     '.ribosomalIntervalsWheader_reorder.txt'),
                'ribosomal-intervals':
                    ('GRCh38/Homo_sapiens.GRCh38.77'
                     '.ribosomalIntervalsWheader_reorder.txt'),
                'snp-bed': 'GRCh38/all_grch38.bed',
                'adapters': 'adapters/smarter_adapter_seqs_3p_5p.fasta'
            },
            'NCBIM37': {
                'gtf': 'NCBIM37/Mus_musculus.NCBIM37.67.gtf',
                'refflat': 'NCBIM37/Mus_musculus.NCBIM37.67.refflat.txt',
                'ribosomal_intervals':
                    ('NCBIM37/Mus_musculus.NCBIM37.67'
                     '.ribosomalIntervalsWheader_reorder.txt'),
                'mtfilter-bed': 'NCBIM37/ncbim37_mitofilter.bed',
                'adapters': 'adapters/smarter_adapter_seqs_3p_5p.fasta'
            },
            'hg19': {
                'mtfilter-bed': 'hg19/hg19_mitofilter.bed',
                'adapters': 'adapters/smarter_adapter_seqs_3p_5p.fasta'
            },
            'mm10': {
                'mtfilter-bed': 'mm10/mm10_mitofilter.bed',
                'adapters': 'adapters/smarter_adapter_seqs_3p_5p.fasta'
            },
            'mm9': {
                'mtfilter-bed': 'mm9/mm9_mitofilter.bed',
                'adapters': 'adapters/smarter_adapter_seqs_3p_5p.fasta'
            }
        }

        ref_type = re.sub('^annotation_', '', parameter['tag'])
        logger.debug("retrieving reference path for build '{}' and type '{}'"
                     .format(self.build, ref_type))
        return 'library::annotation::{}'.format(
            ref_dict[self.build][ref_type]
        )

    def _set_reference_value(self, parameter):
        """
        Given a parameter for a reference option (e.g., a built-in
        genome index) to be set at runtime, return the string value
        for the option based on the current build and reference type.
        """
        ref_dict = {
            'GRCh38': {
                'tophat-index': 'Homo_sapiens-GRCh38',  # 'Homo_sapiens-GRCh38',
                'hisat2-index': 'Homo_sapiens-GRCh38',
                'salmon-index': 'Homo_sapiens-GRCh38',  # 'Human (Homo sapiens): GRCh38',
                'picard-align-index': 'Homo_sapiens-GRCh38',  # 'Homo_sapiens-GRCh38',
                'picard-rnaseq-index': 'Homo_sapiens-GRCh38',  # 'Homo_sapiens-GRCh38',
                'mixcr-species': 'Homo sapiens'
            },
            'NCBIM37': {
                'tophat-index': 'MusMusculus (NCBIM37)',
                'picard-align-index': 'MusMusculus (NCBIM37)',
                'picard-rnaseq-index': 'MusMusculus (NCBIM37)',
                'mixcr-species': 'Mus musculus'
            },
            'hg19': {
                'bowtie2-index': 'hg19',
                'macs2-size': 'hs',
                'picard-align-index': 'hg19'
            },
            'mm10': {
                'bowtie2-index': 'mm10',
                'macs2-size': 'mm',
                'picard-align-index': 'mm10'
            },
            'mm9': {
                'bowtie2-index': 'mm9',
                'macs2-size': 'mm',
                'picard-align-index': 'mm9'
            }
        }
        ref_type = re.sub('^reference_', '', parameter['tag'])
        logger.debug("retrieving reference value for build '{}' and type '{}'"
                     .format(self.build, ref_type))
        try:
            return ref_dict[self.build][ref_type]
        except KeyError:
            logger.exception(("no reference value available for parameter '{}' "
                              "for build '{}'; build '{}' is probably "
                              "unsupported for selected workflow")
                             .format(ref_type, self.build, self.build))
            raise

    def _prep_output_dir(self, output_type):
        """
        Create a subfolder in the ``target_dir`` to store outputs of
        the specified type, return folder path.
        """
        output_dir = os.path.join(self.target_dir, output_type)
        logger.debug("creating folder '{}' to store outputs of type '{}'"
                     .format(output_dir, output_type))
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        return output_dir

    def _build_output_path(self, sample_name, parameter):
        """
        Construct the full path of the current output file, formatted
        with the sample name and source/type-specific file label (as
        well as the appropriate extension).
        """
        output_type_map = {'trimmed': 'TrimmedFastqs',
                           'counts': 'counts',
                           'quant': 'quant',
                           'alignments': 'alignments',
                           'metrics': 'metrics',
                           'qc': 'QC',
                           'trinity': 'Trinity',
                           'assembly': 'assembly',
                           'clones': 'clones',
                           'snps': 'snps',
                           'peaks': 'peaks',
                           'log': 'logs'}

        logger.debug("building output path of parameter '{}' for sample '{}'"
                     .format(parameter['tag'], sample_name))
        output_items = parsing.parse_output_name(parameter['tag'])
        output_dir = self._prep_output_dir(
            output_type_map[output_items['type']]
        )

        out_file = '{}_{}_{}.{}'.format(
            sample_name, output_items['source'], output_items['label'],
            output_items['extension']
        )

        return util.swap_root(os.path.join(output_dir, out_file),
                              'genomics', '/mnt/')

    def _build_sample_parameters(self, sample_path):
        """
        For a given input sample folder, create and set all parameter
        values for input paths, output paths, and other options.
        """
        sample_id = parsing.get_sample_id(sample_path)
        fc_id = parsing.get_flowcell_id(sample_path)
        sample_name = '{}_{}'.format(sample_id, fc_id).rstrip('_')

        logger.debug("setting parameter values for sample '{}'"
                     .format(sample_name))
        param_values = []
        for param in self.parameters:
            logger.debug("... current parameter: {}".format(param))
            if re.search('endpoint', param['name']):
                param_values.append(self.endpoint)

            elif param['type'] == 'sample':
                param_values.append(sample_name)
            elif param['type'] == 'input':
                lane = re.search('[1-8]', param['name']).group()
                param_values.append(
                    util.swap_root(
                        self._get_lane_fastq(sample_path, lane),
                        'genomics', '/mnt/'
                    )
                )
            elif param['type'] == 'annotation':
                param_values.append(self._build_reference_path(param))
            elif param['type'] == 'reference':
                param_values.append(self._set_reference_value(param))
            elif param['type'] == 'output':
                if re.search('^fastq_out', param['tag']):
                    final_fastq = '{}_R1-final.fastq.gz'.format(sample_name)
                    output_path = os.path.join(
                        util.swap_root(self.target_dir, 'genomics', '/mnt/'),
                        'inputFastqs', final_fastq
                    )
                else:
                    output_path = self._build_output_path(sample_name, param)
                param_values.append(output_path)
            logger.debug("... value set: '{}'".format(param_values[-1]))

        return param_values

    def parameterize(self):
        """
        Set all parameter values for the current workflow and input
        samples and return as list of sample parameters.

        :rtype: list
        :return: List of lists, where the original input list of
            parameter dicts has been replicated for each sample and
            updated to include values specific for that sample.
        """
        sample_params = []
        for s in self.sample_paths:
            logger.debug("setting parameters for input sample file '{}'"
                         .format(s))
            s_values = self._build_sample_parameters(s)
            s_params = []
            for idx, v in enumerate(s_values):
                s_param = self.parameters[idx].copy()
                s_param['value'] = s_values[idx]
                s_params.append(s_param)
            sample_params.append(s_params)

        self.samples = sample_params









