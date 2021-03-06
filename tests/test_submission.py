import logging
import os
import re
import datetime

import mock
import mongomock
import pytest

from bripipetools import annotation
from bripipetools import submission

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def mock_db():
    # GIVEN a mock_ed version of the TG3 Mongo database
    logger.info(("[setup] mock_ database, connect "
                 "to mock Mongo database"))

    yield mongomock.MongoClient().db
    logger.debug(("[teardown] mock_ database, disconnect "
                  "from mock Mongo database"))


@pytest.fixture(scope='function')
def mock_params():
    yield [{'tag': 'SampleName', 'type': 'sample', 'name': 'SampleName'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_endpoint'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path4'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path5'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path6'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path7'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path1'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path2'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path3'},
           {'tag': 'fastq_in', 'type': 'input', 'name': 'from_path8'},
           {'tag': 'annotation_gtf', 'type': 'annotation', 'name': 'gtfFile'},
           {'tag': 'annotation_adapters', 'type': 'annotation', 'name': 'adapterFile'},
           {'tag': 'annotation_ribosomal_intervals', 'type': 'annotation', 'name': 'ribointsFile'},
           {'tag': 'annotation_refflat', 'type': 'annotation', 'name': 'refflatFile'},
           {'tag': 'tophat_alignments_bam_out', 'type': 'output', 'name': 'to_endpoint'},
           {'tag': 'tophat_alignments_bam_out', 'type': 'output', 'name': 'to_path'}]


class TestBatchParameterizer:
    """

    """
    def test_get_lane_order(self, mock_params):
        # mock_filename = '161231_P00-00_C00000XX_optimized_workflow_1.txt'
        # mock_file = mock_template(mock_filename, tmpdir)
        mock_paths = ['lib1111-11111111', 'lib2222-22222222']

        parameterizer = submission.BatchParameterizer(
            sample_paths=mock_paths,
            parameters=mock_params,
            endpoint='',
            target_dir=''
        )

        logger.debug("{}".format(parameterizer.parameters))
        assert (parameterizer._get_lane_order()
                == ['4', '5', '6', '7', '1', '2', '3', '8'])

    def test_get_lane_fastq_when_lane_exists(self, mock_params, tmpdir):
        mock_path = tmpdir.mkdir('lib1111-11111111')
        mock_lane = '2'
        mock_fastqpath = mock_path.ensure(
            'sample-name_S001_L00{}_R1_001.fastq.gz'.format(mock_lane)
        )

        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir=''
        )

        test_fastqpath = parameterizer._get_lane_fastq(str(mock_path), mock_lane)

        assert (test_fastqpath == mock_fastqpath)

    def test_get_lane_fastq_when_lane_missing(self, mock_params, tmpdir):
        mock_path = tmpdir.mkdir('lib1111-11111111')
        mock_lane = '2'
        mock_path.ensure('sample-name_S001_L001_R1_001.fastq.gz')
        mock_fastqpath = mock_path.join('empty_L00{}_R1.fastq.gz'
                                        .format(mock_lane))

        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir=''
        )

        test_fastqpath = parameterizer._get_lane_fastq(str(mock_path), mock_lane)

        assert (test_fastqpath == mock_fastqpath)

    def test_build_reference_path(self, mock_params):
        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir=''
        )

        mock_param = {'tag': 'annotation_gtf',
                      'type': 'annotation',
                      'name': 'gtfFile'}

        test_path = parameterizer._build_reference_path(mock_param)

        mock_path = 'library::annotation::GRCh38/Homo_sapiens.GRCh38.77.gtf'
        assert (test_path == mock_path)

    def test_set_option_value(self, mock_params):
        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir='',
            build='GRCh38',
        )

        mock_param = {'tag': 'option_tophat',
                      'type': 'option',
                      'name': 'index'}

        test_value = parameterizer._set_option_value(mock_param)

        mock_value = 'GRCh38'
        assert (test_value == mock_value)

    def test_set_option_value_invalid_build(self, mock_params):
        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir='',
            build='GRCh38'
        )

        mock_param = {'tag': 'option_bowtie2',
                      'type': 'option',
                      'name': 'index'}

        with pytest.raises(KeyError):
            parameterizer._set_option_value(mock_param)

    def test_set_option_value_not_stranded(self, mock_params):
        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir='',
            build='GRCh38',
        )

        mock_param = {'tag': 'option_tophat',
                      'type': 'option',
                      'name': 'library_type'}

        test_value = parameterizer._set_option_value(mock_param)

        mock_value = 'fr-unstranded'
        assert (test_value == mock_value)

    def test_set_option_value_stranded(self, mock_params):
        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir='',
            build='GRCh38',
            stranded=True
        )

        mock_param = {'tag': 'option_tophat',
                      'type': 'option',
                      'name': 'library_type'}

        test_value = parameterizer._set_option_value(mock_param)

        mock_value = 'fr-firststrand'
        assert (test_value == mock_value)

    def test_prep_output_dir(self, mock_params, tmpdir):
        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir=str(tmpdir)
        )

        mock_outtype = 'counts'
        mock_path = tmpdir.join(mock_outtype)

        test_path = parameterizer._prep_output_dir(mock_outtype)

        assert (test_path == mock_path)
        assert (os.path.exists(test_path))
        assert (os.path.isdir(test_path))

    def test_build_output_path(self, mock_params, tmpdir):
        mock_targetdir = tmpdir.mkdir('pipeline')

        parameterizer = submission.BatchParameterizer(
            sample_paths=[],
            parameters=mock_params,
            endpoint='',
            target_dir=str(mock_targetdir)
        )

        mock_sample = 'lib1111_C00000XX'
        mock_param = {'tag': 'tophat_alignments_bam_out',
                      'type': 'output',
                      'name': 'to_path'}

        test_path = parameterizer._build_output_path(mock_sample, mock_param)

        mock_path = os.path.join('/mnt/bioinformatics/pipeline/alignments',
                                 'lib1111_C00000XX_tophat_alignments.bam')
        assert (test_path == mock_path)

    def test_build_sample_parameters(self, mock_params, tmpdir):
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_path = (tmpdir
                    .mkdir('bioinformatics')
                    .mkdir('pipeline')
                    .mkdir(mock_runid)
                    .mkdir('lib1111-11111111'))
        mock_fastqpath = mock_path.ensure(
            'sample-name_S001_L001_R1_001.fastq.gz'
        )
        mock_fastqpath = re.sub(str(tmpdir), '/mnt', str(mock_fastqpath))
        mock_emptypaths = {
            lane: re.sub(
                str(tmpdir), '/mnt', str(mock_path.join(
                    'empty_L00{}_R1.fastq.gz'.format(lane))
                )
            )
            for lane in range(2, 9)
            }

        mock_endpoint = 'benaroyaresearch#BRIGridFTP'
        mock_targetdir = (tmpdir.join('pipeline').join(mock_runid))

        parameterizer = submission.BatchParameterizer(
            sample_paths=[str(mock_path)],
            parameters=mock_params,
            endpoint=mock_endpoint,
            target_dir=str(mock_targetdir)
        )

        test_values = parameterizer._build_sample_parameters(str(mock_path))

        mock_refpaths = [
            'library::annotation::GRCh38/Homo_sapiens.GRCh38.77.gtf',
            'library::annotation::adapters/smarter_adapter_seqs_3p_5p.fasta',
            ('library::annotation::GRCh38/Homo_sapiens.GRCh38.77'
             '.ribosomalIntervalsWheader_reorder.txt'),
            'library::annotation::GRCh38/Homo_sapiens.GRCh38.77.refflat.txt',
        ]

        mock_samplename = 'lib1111_C00000XX'
        mock_outpath = os.path.join(
            '/mnt/bioinformatics/pipeline/', mock_runid,
            'alignments', 'lib1111_C00000XX_tophat_alignments.bam'
        )
        mock_values = ([mock_samplename,
                        mock_endpoint, mock_emptypaths[4], mock_emptypaths[5],
                        mock_emptypaths[6], mock_emptypaths[7],
                        mock_fastqpath, mock_emptypaths[2], mock_emptypaths[3],
                        mock_emptypaths[8]]
                       + mock_refpaths
                       + [mock_endpoint, mock_outpath])
        assert (test_values == mock_values)

    def test_parameterize(self, mock_params, tmpdir):
        tmpdir = tmpdir.mkdir('bioinformatics').mkdir('pipeline')
        mock_paths = [str(tmpdir.mkdir('lib1111-11111111')),
                      str(tmpdir.mkdir('lib2222-22222222'))]

        parameterizer = submission.BatchParameterizer(
            sample_paths=mock_paths,
            parameters=mock_params,
            endpoint='',
            target_dir=str(tmpdir)
        )

        parameterizer.parameterize()
        test_params = parameterizer.samples

        assert (len(test_params) == len(mock_paths))
        assert (test_params[0][0]
                == {'tag': 'SampleName',
                    'type': 'sample',
                    'name': 'SampleName',
                    'value': 'lib1111'})


#@pytest.fixture(scope='function')
def mock_template(filename, tmpdir):
    # GIVEN a simplified workflow batch content with protypical contents
    mock_params = ['SampleName',
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_endpoint'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path4'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path5'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path6'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path7'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path1'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path2'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path3'),
                   ('fastq_in##Param::2942::'
                    'globus_get_data_flowcell_text::from_path8'),
                   'annotation_gtf##SourceType::SourceName::gtfFile',
                   'annotation_adapters##SourceType::SourceName::adapterFile',
                   ('annotation_ribosomal_intervals##SourceType::'
                    'SourceName::ribointsFile'),
                   'annotation_refflat##SourceType::SourceName::refflatFile',
                   ('tophat_alignments_bam_out##Param::2946::'
                    'globus_send_data::to_endpoint'),
                   ('tophat_alignments_bam_out##Param::2946::'
                    'globus_send_data::to_path')]

    mock_contents = ['###METADATA\n',
                     '#############\n',
                     'Workflow Name\toptimized_workflow_1\n',
                     'Workflow id\tba1f5a6a3d5eec2c\n',
                     'Project Name\t<Your_project_name>\n',
                     '###TABLE DATA\n',
                     '#############\n',
                     '{}\t'.format('\t'.join(mock_params))]
    mock_file = tmpdir.join(filename)
    mock_file.write(''.join(mock_contents))
    return str(mock_file)


class TestBatchCreator:
    """

    """
    def test_build_batch_name_with_defaults(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        creator = submission.BatchCreator(
            paths=[],
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir)
        )

        test_name = creator._build_batch_name()

        mock_date = datetime.date.today().strftime("%y%m%d")
        mock_name = '{}__optimized_workflow_1_GRCh38.77_unstrand'.format(
            mock_date
        )

        assert (test_name == mock_name)

    def test_build_batch_name_with_tags(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)
        mock_grouptag = 'C00000XX'
        mock_subgrouptags = ['P1-1', 'P99-99']

        creator = submission.BatchCreator(
            paths=[],
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag=mock_grouptag,
            subgroup_tags=mock_subgrouptags
        )

        test_name = creator._build_batch_name()

        mock_date = datetime.date.today().strftime("%y%m%d")
        mock_name = '{}_{}_{}_optimized_workflow_1_GRCh38.77_unstrand'.format(
                mock_date, mock_grouptag, '_'.join(mock_subgrouptags)
        )

        assert (test_name == mock_name)

    def test_get_sample_paths_for_folders(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                folderpath.mkdir(s)

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        creator._check_input_type()

        assert creator.inputs_are_folders

    def test_get_sample_paths_for_samples(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_paths.append(str(samplepath))
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        creator._check_input_type()

        assert not creator.inputs_are_folders

    def test_get_sample_paths_for_empty_samples(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_paths.append(str(samplepath))

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        with pytest.raises(IndexError):
            creator._check_input_type()

    def test_prep_target_dir_for_folder(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        test_path = creator._prep_target_dir(mock_paths[0])

        mock_date = datetime.date.today().strftime("%y%m%d")
        mock_path = tmpdir.join(
            'Project_P1-1Processed_globus_{}'.format(mock_date)
        )

        assert (test_path == mock_path)
        assert os.path.isdir(str(mock_path))

    def test_prep_target_dir_for_samples(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_paths.append(str(samplepath))

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='Mock',
            subgroup_tags=''
        )

        test_path = creator._prep_target_dir()

        mock_date = datetime.date.today().strftime("%y%m%d")
        mock_path = tmpdir.join(
            'Project_MockProcessed_globus_{}'.format(mock_date)
        )

        assert (test_path == mock_path)
        assert os.path.isdir(str(mock_path))

    def test_get_sample_paths_with_defaults(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        mock_samplepaths = {}
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_samplepaths.setdefault(idx, []).append(str(samplepath))
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        test_samplepaths = creator._get_sample_paths(mock_paths[0])

        assert (test_samplepaths == mock_samplepaths[0])

    def test_get_sample_paths_with_num_samples_opt(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        mock_samplepaths = {}
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_samplepaths.setdefault(idx, []).append(str(samplepath))
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags='',
            num_samples=1,
        )

        test_samplepaths = creator._get_sample_paths(mock_paths[0])

        assert (test_samplepaths == mock_samplepaths[0][0:1])

    def test_get_sample_paths_with_sort_opt(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        mock_samplepaths = {}
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_samplepaths.setdefault(idx, []).append(str(samplepath))
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                filepath = samplepath.ensure(
                    'sample-name_S001_L002_R1_001.fastq.gz'
                )
                if s == mock_samples[idx][0]:
                    filepath.write('mock contents\n')

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags='',
            sort=True,
            num_samples=1
        )

        test_samplepaths = creator._get_sample_paths(mock_paths[0])

        assert (test_samplepaths == mock_samplepaths[0][1:])

    def test_get_input_params_for_folders(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        test_params = creator._get_input_params()

        assert (len(test_params) == 4)
        assert (test_params[0][0]['value'] == 'lib1111')

    def test_get_input_params_for_samples(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                mock_paths.append(str(samplepath))
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint='',
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        test_params = creator._get_input_params()

        assert (len(test_params) == 4)
        assert (test_params[0][0]['value'] == 'lib1111')

    def test_create_batch(self, tmpdir):
        mock_filename = 'optimized_workflow_1.txt'
        mock_file = mock_template(mock_filename, tmpdir)

        mock_folders = ['P1-1-11111111', 'P99-99-99999999']
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_folders):
            folderpath = tmpdir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        mock_endpoint = 'benaroyaresearch#BRIGridFTP'

        creator = submission.BatchCreator(
            paths=mock_paths,
            workflow_template=mock_file,
            endpoint=mock_endpoint,
            base_dir=str(tmpdir),
            group_tag='',
            subgroup_tags=''
        )

        test_path = creator.create_batch()
        with open(test_path) as f:
            test_contents = f.readlines()
        logger.debug("{}".format(test_contents))

        assert (len([l for l in test_contents
                     if re.search('^lib', l)])
                == 4)


class TestFlowcellSubmissionBuilder:
    """

    """
    def test_init_annotator(self, mock_db):
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_path = '/mnt/bioinformatics/pipeline/Illumina/{}'.format(mock_runid)
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'

        builder = submission.FlowcellSubmissionBuilder(
            path=mock_path,
            endpoint=mock_endpoint,
            db=mock_db
        )

        builder._init_annotator()
        assert (type(builder.annotator) == annotation.FlowcellRunAnnotator)

    def test_get_workflow_options_for_all_workflows(self, mock_db, tmpdir):
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_path = '/mnt/bioinformatics/pipeline/Illumina/{}'.format(mock_runid)
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'

        mock_workflowdir = tmpdir.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [str(mock_workflowdir.ensure(w))
                             for w in mock_workflows]
        mock_workflowopts.sort()

        builder = submission.FlowcellSubmissionBuilder(
            path=mock_path,
            endpoint=mock_endpoint,
            db=mock_db,
            workflow_dir=str(mock_workflowdir)
        )

        test_workflowopts = builder.get_workflow_options(optimized_only=False)

        assert (test_workflowopts == mock_workflowopts)

    def test_get_workflow_options_for_optimized_workflows(self, mock_db,
                                                          tmpdir):
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_path = '/mnt/bioinformatics/pipeline/Illumina/{}'.format(mock_runid)
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'

        mock_workflowdir = tmpdir.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [str(mock_workflowdir.ensure(w))
                             for w in mock_workflows
                             if re.search('optimized', w)]
        mock_workflowopts.sort()

        builder = submission.FlowcellSubmissionBuilder(
            path=mock_path,
            endpoint=mock_endpoint,
            db=mock_db,
            workflow_dir=str(mock_workflowdir)
        )

        test_workflowopts = builder.get_workflow_options()

        assert (test_workflowopts == mock_workflowopts)

    def test_get_projects(self, mock_db, tmpdir):
        # GIVEN a flowcell run ID and an arbitrary root directory,
        # under which a folder exists at 'bioinformatics/pipeline/Illumina/<run_id>',
        # and that folder contains a subfolder named 'Unaligned'
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'

        # AND the unaligned folder includes multiple project folders
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_path = (tmpdir
                    .mkdir('bioinformatics')
                    .mkdir('pipeline')
                    .mkdir('Illumina')
                    .mkdir(mock_runid))
        mock_unaligndir = mock_path.mkdir('Unaligned')
        mock_paths = [mock_unaligndir.mkdir(p) for p in mock_projects]

        builder = submission.FlowcellSubmissionBuilder(
            path=str(mock_path),
            endpoint=mock_endpoint,
            db=mock_db
        )

        builder._get_project_paths()

        assert (builder.project_paths == mock_paths)

    def test_assign_workflows(self, mock_db, tmpdir):
        # GIVEN a flowcell run ID and an arbitrary root directory,
        # under which a folder exists at 'bioinformatics/pipeline/Illumina/<run_id>',
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'
        mock_path = (tmpdir
                    .mkdir('bioinformatics')
                    .mkdir('pipeline')
                    .mkdir('Illumina')
                    .mkdir(mock_runid))
        
        # AND that folder contains a subfolder named 'Unaligned'
        mock_unaligndir = mock_path.mkdir('Unaligned')

        # AND the unaligned folder includes multiple project folders
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_paths = [str(mock_unaligndir.mkdir(p)) for p in mock_projects]

        # WHEN a flowcell submission is built using the available workflows
        mock_workflowdir = mock_path.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [str(mock_workflowdir.ensure(w))
                             for w in mock_workflows
                             if re.search('optimized', w)]
        mock_workflowopts.sort()

        mock_buildopts = ['GRCh38.77', 'NCBIM37.67', 'mm10']
        
        builder = submission.FlowcellSubmissionBuilder(
            path=str(mock_path),
            endpoint=mock_endpoint,
            db=mock_db,
            workflow_dir=str(mock_workflowdir)
        )

        with mock.patch('builtins.input',
                        side_effect=iter(["0", "0", "0", "", ""])):
            builder._assign_workflows()

        # THEN the workflow builder will generate workflow batch files
        # and store the paths to these files in a batch map
        mock_batchkey = (mock_workflowopts[0], mock_buildopts[0], False)
        assert (builder.batch_map == {mock_batchkey: [mock_paths[0]]})

    def test_get_batch_tags(self, mock_db, tmpdir):
        # GIVEN a flowcell run ID and an arbitrary root directory,
        # under which a folder exists at 'bioinformatics/pipeline/Illumina/<run_id>',
        # and that folder contains a subfolder named 'Unaligned'
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'

        # AND the unaligned folder includes multiple project folders
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_path = (tmpdir
                    .mkdir('bioinformatics')
                    .mkdir('pipeline')
                    .mkdir('Illumina')
                    .mkdir(mock_runid))
        mock_unaligndir = mock_path.mkdir('Unaligned')
        mock_paths = [str(mock_unaligndir.mkdir(p)) for p in mock_projects]

        builder = submission.FlowcellSubmissionBuilder(
            path=str(mock_path),
            endpoint=mock_endpoint,
            db=mock_db
        )

        test_grouptag, test_subgrouptags = builder._get_batch_tags(mock_paths)

        assert (test_grouptag == 'C00000XX')
        assert (test_subgrouptags == ['P1-1', 'P99-99'])

    def test_run(self, mock_db, tmpdir):
        # GIVEN a flowcell run ID and an arbitrary root directory,
        # under which a folder exists at 'bioinformatics/pipeline/Illumina/<run_id>',
        # and that folder contains a subfolder named 'Unaligned'
        mock_runid = '161231_INSTID_0001_AC00000XX'
        mock_endpoint = 'benaroyaresearch#BRIGridFTP'
        mock_path = (tmpdir
                    .mkdir('bioinformatics')
                    .mkdir('pipeline')
                    .mkdir('Illumina')
                    .mkdir(mock_runid))

        mock_workflowdir = mock_path.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [mock_template(w, mock_workflowdir)
                             for w in mock_workflows
                             if re.search('optimized', w)]
        mock_workflowopts.sort()

        mock_buildopts = ['GRCh38.77', 'NCBIM37.67', 'mm10']

        # AND the unaligned folder includes multiple project folders
        mock_projects = ['P1-1-11111111', 'P99-99-99999999']
        mock_unaligndir = mock_path.mkdir('Unaligned')
        mock_samples = {0: ['lib1111-11111111', 'lib2222-22222222'],
                        1: ['lib3333-33333333', 'lib4444-44444444']}
        mock_paths = []
        for idx, f in enumerate(mock_projects):
            folderpath = mock_unaligndir.mkdir(f)
            mock_paths.append(str(folderpath))
            for s in mock_samples[idx]:
                samplepath = folderpath.mkdir(s)
                samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
                samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        builder = submission.FlowcellSubmissionBuilder(
            path=str(mock_path),
            endpoint=mock_endpoint,
            db=mock_db,
            workflow_dir=str(mock_workflowdir)
        )

        builder.batch_map = {
            (mock_workflowopts[0], mock_buildopts[0], False): [mock_paths[0]]
        }
        test_paths = builder.run()

        with open(test_paths[0]) as f:
            test_contents = f.readlines()

        mock_date = datetime.date.today().strftime("%y%m%d")
        mock_paths = [os.path.join(
            str(mock_path),
            'globus_batch_submission',
            '{}_C00000XX_P1-1_optimized_workflow1_GRCh38.77_unstrand.txt'.format(
                mock_date
            )
        )]

        assert (test_paths == mock_paths)
        assert (len([l for l in test_contents
                     if re.search('^lib', l)])
                == 2)


class TestSampleSubmissionBuilder:
    """

    """
    def test_read_paths(self, tmpdir):
        mock_workflowdir = tmpdir.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [str(mock_workflowdir.ensure(w))
                             for w in mock_workflows]
        mock_workflowopts.sort()

        # mock_filename = 'optimized_workflow_1.txt'
        # mock_file = mock_template(mock_filename, tmpdir)

        mock_samples = ['lib1111-11111111', 'lib2222-22222222']
        mock_paths = []
        for s in mock_samples:
            samplepath = tmpdir.mkdir(s)
            mock_paths.append(str(samplepath))
            samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
            samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        mock_manifest = tmpdir.join('manifest.txt')
        mock_manifest.write('\n'.join(mock_paths))

        builder = submission.SampleSubmissionBuilder(
            manifest=str(mock_manifest),
            out_dir=str(tmpdir),
            endpoint='',
            workflow_dir=str(mock_workflowdir)
        )

        builder._read_paths()

        assert (builder.paths == mock_paths)

    def test_get_workflow_options_for_all_workflows(self, tmpdir):
        mock_workflowdir = tmpdir.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [str(mock_workflowdir.ensure(w))
                             for w in mock_workflows]
        mock_workflowopts.sort()

        builder = submission.SampleSubmissionBuilder(
            manifest='',
            out_dir=str(tmpdir),
            endpoint='',
            workflow_dir=str(mock_workflowdir)
        )

        test_workflowopts = builder.get_workflow_options(optimized_only=False)

        assert (test_workflowopts == mock_workflowopts)

    def test_assign_workflow(self, tmpdir):
        mock_workflowdir = tmpdir.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [str(mock_workflowdir.ensure(w))
                             for w in mock_workflows]
        mock_workflowopts.sort()

        mock_buildopts = ['GRCh38.77', 'NCBIM37.67', 'mm10']

        mock_samples = ['lib1111-11111111', 'lib2222-22222222']
        mock_paths = []
        for s in mock_samples:
            samplepath = tmpdir.mkdir(s)
            mock_paths.append(str(samplepath))
            samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
            samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        builder = submission.SampleSubmissionBuilder(
            manifest='',
            out_dir=str(tmpdir),
            endpoint='',
            workflow_dir=str(mock_workflowdir)
        )

        builder.paths = mock_paths

        with mock.patch('builtins.input',
                        side_effect=iter(["0", "0"])):
            builder._assign_workflow()

        mock_batchkey = (mock_workflowopts[0], mock_buildopts[0])
        assert (builder.batch_map == {mock_batchkey: mock_paths})

    def test_run(self, tmpdir):
        mock_workflowdir = tmpdir.mkdir('galaxy_workflows')
        mock_workflows = ['workflow1.txt', 'optimized_workflow1.txt']
        mock_workflowopts = [mock_template(w, mock_workflowdir)
                             for w in mock_workflows
                             if re.search('optimized', w)]
        mock_workflowopts.sort()

        mock_buildopts = ['GRCh38.77', 'NCBIM37.67', 'mm10']

        mock_samples = ['lib1111-11111111', 'lib2222-22222222']
        mock_paths = []
        for s in mock_samples:
            samplepath = tmpdir.mkdir(s)
            mock_paths.append(str(samplepath))
            samplepath.ensure('sample-name_S001_L001_R1_001.fastq.gz')
            samplepath.ensure('sample-name_S001_L002_R1_001.fastq.gz')

        builder = submission.SampleSubmissionBuilder(
            manifest='',
            out_dir=str(tmpdir),
            endpoint='',
            workflow_dir=str(mock_workflowdir)
        )

        mock_batchkey = (mock_workflowopts[0], mock_buildopts[0])
        builder.batch_map = {mock_batchkey: mock_paths}

        test_batchpaths = builder.run()

        with open(test_batchpaths[0]) as f:
            test_contents = f.readlines()
        logger.debug("{}".format(test_contents))

        mock_date = datetime.date.today().strftime("%y%m%d")
        mock_batchpaths = [os.path.join(
            str(tmpdir),
            '{}__optimized_workflow1_GRCh38.77_unstrand.txt'.format(mock_date)
        )]

        assert (test_batchpaths == mock_batchpaths)
        assert (len([l for l in test_contents
                     if re.search('^lib', l)])
                == 2)
