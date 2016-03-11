from bioblend import galaxy
import requests, re, os, json, zipfile, StringIO, csv

class SessionManager(object):

    def __init__(self, user_num=None, galaxy_user=None, galaxy_server=None,
                 galaxy_instance=None, galaxy_session=None,
                 include_results=None, target_dir=None):

        if not galaxy_user:
            if user_num is None:
                self.select_user()
            else:
                self.select_user(user_num)
        else:
            self.gu = galaxy_user

        if not galaxy_server:
            self.server = 'http://srvgalaxy02'
        else:
            self.server = galaxy_server

        if not galaxy_instance:
            self.connect_to_galaxy_api()
        else:
            self.gi = galaxy_instance

        if not galaxy_session:
            self.connect_to_galaxy_server()
        else:
            self.gs = galaxy_session

        self.rd = include_results

    def select_user(self, user_num=None):

        # Load list of known users
        with open('../data/users.json') as f:
            users = json.load(f)

        # Select user number
        if user_num is None:
            print "\nFound the following users:"
            for t,u in enumerate(users):
                print "%3d : %s" % (t, users[u].get('username'))

            un = raw_input("Type the number of the user you wish to select: ")
        else:
            un = user_num

        self.user = users[users.keys()[int(un)]]

    def connect_to_galaxy_api(self):

        # Connect to Galaxy API
        galaxy_instance = galaxy.GalaxyInstance(url=self.server,
                                                key=self.user.get('api_key'))
        self.gi = galaxy_instance

    def connect_to_galaxy_server(self):

        # Log into Galaxy server
        login_payload = {'email': self.user.get('username'),
                         'redirect': self.server,
                         'password': self.user.get('password'),
                         'login_button': 'Login'}
        galaxy_session = requests.session()
        login = galaxy_session.post(url=self.server + '/user/login?use_panels=True',
                                    data=login_payload)
        self.gs = galaxy_session

    def add_target_dir(self, target_dir=None):
        self.dir = target_dir

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)


###################################

class HistoryManager(object):
    """
    Class with methods for inspecting and performing operations with a Galaxy History.
    """
    def __init__(self, galaxy_instance, history_id=None):
        self.gi = galaxy_instance

        if not history_id:
            self.select_history()
        else:
            self.hid = history_id
            self.hname = self.gi.histories.get_histories(self.hid)[0].get('name')

    def select_history(self):
        """
        Select current Galaxy History.
        """
        # Get list of histories on Galaxy and print as user options
        history_list = self.gi.histories.get_histories()
        print "\nFound the following histories:"
        for t,h in enumerate(history_list):
            print "%3d : %s" % (t, h.get('name'))

        # For the selected history, get the ID and full history contents
        var = raw_input("Type the number of the History you wish to select: ")
        history = history_list[int(var)]
        self.hid = history.get('id')
        self.hname = history.get('name')

    def get_datasets(self):
        """
        Get list of all Datasets in History.
        """
        dataset_list = self.gi.histories.show_history(self.hid, contents=True)
        self.dl = [d for d in dataset_list if not d.get('deleted')]

    def show_datasets(self):
        """
        View list of History Datasets.
        """
        if not hasattr(self, 'dl'):
            self.get_datasets()

        return self.dl

    def annotate_dataset_list(self):
        def clean_dataset_name(dataset_name=None):
            """
            Format a Dataset name (to make it generic).
            """
            dataset_name = re.sub("lib.*fastq", "input FASTQ", dataset_name)
            dataset_name = re.sub(" on data [0-9]+( and data [0-9]+)*", "",
                                  dataset_name)
            dataset_name = re.sub("_.*(\:|\.)+", ": ", dataset_name)

            return dataset_name

        dataset_dict = {d.get('id'):
                        {'name': clean_dataset_name(d.get('name')),
                         'num': d.get('hid')} for d in self.dl}

        self.dd = dataset_dict

    # def get_dataset_name(self, dataset_id):
    #     """
    #     Get Dataset name corresponding to ID.
    #     """
    #     dc = self.gi.datasets
    #     dataset_name = dc.show_dataset(dataset_id).get('name')
    #
    #     return self.clean_dataset_name(dataset_name)

    def build_dataset_graph(self, dataset_graph={}):
        """
        Build graph representing input/output relationship of all Datasets in
        current History.
        """
        if not hasattr(self, 'dl'):
            self.get_datasets()

        get_provenance = self.gi.histories.show_dataset_provenance

        for d in self.dl:
            out_id = d.get('id')

            dataset_params = get_provenance(self.hid, out_id).get('parameters')

            dataset_inputs = [dataset_params[p].get(f) \
                              for p in dataset_params \
                              for f in dataset_params[p] \
                              if re.search('^id$', f)]

            if len(dataset_inputs):
                for d in dataset_inputs:
                    if d in dataset_graph:
                        dataset_graph[d] = list(set(dataset_graph[d] + [out_id]))
                    else:
                        dataset_graph[d] = [out_id]

        self.dg = dataset_graph

    def show_dataset_graph(self):
        """
        View graph (dictionary) with input/output relationship for all
        Datasets in History.
        """
        if not hasattr(self, 'dg'):
            self.build_dataset_graph()

        return self.dg

    def get_root_datasets(self):
        """
        Based on the Dataset graph, identify root Datasets in the History.
        """
        if not hasattr(self, 'dg'):
            self.build_dataset_graph()

        output_dataset_list = [o for outputs in self.dg.values() \
                               for o in outputs]
        root_dataset_list = [d for d in self.dl \
                             if d.get('id') not in output_dataset_list]
        self.rdl = root_dataset_list

    def show_root_datasets(self):
        """
        Show list of root Datasets in current History.
        """
        if not hasattr(self, 'rdl'):
            get_root_datasets()

        return self.rdl

    def get_input_datasets(self):
        """
        Get list of input (non-reference) Datasets for current History.
        """
        if not hasattr(self, 'rdl'):
            self.get_root_datasets()

        input_dataset_list = [{d.get('id'): d.get('name')} \
            for d in self.rdl \
            if re.search('incoming',
            self.gi.datasets.show_dataset(d.get('id')).get('file_name'))]

        self.idl = input_dataset_list

    def show_input_datasets(self):
        """
        View list of input (non-reference) Datasets for History.
        """
        if not hasattr(self, 'idl'):
            self.get_input_datasets()

        return self.idl

    def collect_history_info(self):
        if not hasattr(self, 'idl'):
            self.get_input_datasets()
        if not hasattr(self, 'dd'):
            self.annotate_dataset_list()

###################################

class ResultCollector(object):
    """
    Class with methods for collecting information about all downstream
    (output) Datasets for current input Dataset.
    """
    def __init__(self, history_manager=None, input_dataset=None):

        self.hm = history_manager

        self.id = input_dataset.keys()[0]
        self.file = input_dataset.values()[0]
        self.lib = re.search('lib[0-9]+(.*(XX)+)*',
                              self.file).group()

    def build_summary_graph(self, input_dataset=None, summary_graph={}):
        """
        Trace path from a single input to all outputs.
        """
        if not input_dataset:
            input_id = self.id
        else:
            input_id = input_dataset

        self.sg = summary_graph

        if isinstance(input_id, list):
            [self.build_summary_graph(i, self.sg) for i in input]
        if input_id in self.hm.dg:
            [self.build_summary_graph(i, self.sg) \
             for i in self.hm.dg[input_id]]

            self.sg[input_id] = [i for i in self.hm.dg[input_id]]

        return self.sg

    def get_input_outputs(self, input_id=None, input_output_list=[]):
        """
        Get list of all output Datasets downstream of current input Dataset.
        """
        if not input_id:
            input_id = self.id

        self.iol = input_output_list

        if input_id in self.hm.dg:
            self.iol = list(set(self.iol + self.hm.dg[input_id]))

            for d in self.hm.dg[input_id]:
                self.iol = self.get_input_outputs(d, self.iol)

        return self.iol

    def annotate_output_list(self):

        if not hasattr(self, 'iol'):
            self.get_input_outputs()
        if not hasattr(self, 'sg'):
            self.build_summary_graph()

        def get_info(dataset_id):
            dname = self.hm.dd[dataset_id].get('name')
            dnum = self.hm.dd[dataset_id].get('num')

            return (dname, dnum)

        self.ol = []
        for output in self.iol:
            dname,dnum = get_info(output)
            priors = ['%s (%d)' % get_info(d) \
                      for d in self.sg if output in self.sg[d]][0]
            self.ol.append({'id': output, 'num': dnum,
                                'name': dname, 'prior': priors})


    def flag_duplicate_outputs(self, output_list):
        seen = set()
        seen_add = seen.add

        # find final versions of duplicated outputs
        duplicated = { x.get('name'): i \
                       for i,x in enumerate(output_list) \
                       if x.get('name') in seen or seen_add(x.get('name')) }

        # remove duplicated outputs if not final version
        not_final = [i for i,x in enumerate(output_list) \
                     if x.get('name') in duplicated \
                     and not i == duplicated[x.get('name')]]

        for i in not_final:
            output_list[i]['name'] = 'skip_' + output_list[i]['name']

        return output_list

    def show_output_list(self):

        if not hasattr(self, 'ol'):
            self.annotate_output_list()

        get_hid = self.hm.gi.histories.show_dataset
        sorted_output_list = sorted(self.ol, key=lambda x: x.get('num'))
        final_output_list = self.flag_duplicate_outputs(sorted_output_list)

        return sorted_output_list


###################################

class ResultDownloader(object):

    def __init__(self, session_manager, lib_id, output=None,
                 result_type=None):

        self.gi = session_manager.gi
        self.gs = session_manager.gs
        self.dir = session_manager.dir
        self.rd = session_manager.rd
        self.lib = lib_id


        if output is not None:
            self.parse_output(output)

        with open('../data/params.json') as f:
            self.params = json.load(f)

        if not result_type:
            self.get_result_type()

        self.state = 'idle'

    def parse_output(self, output):
        self.dname = output.get('name')
        self.oid = output.get('id')
        self.prior = output.get('prior')
        self.label = '%s (%d)' % (self.dname, output.get('num'))

    def check_macs2_version(self):

        history_id = (self.gi.datasets
                        .show_dataset(self.oid)
                        .get('history_id'))
        macs2_params = (self.gi.histories
                            .show_dataset_provenance(history_id, self.oid)
                            .get('parameters')
                            .get('advanced_options'))

        if 'broad' in macs2_params:
            self.macs2v = '_broad'
        else:
            self.macs2v = ''

    def get_result_type(self, result_type=None):

        dname = self.dname
        if re.search('macs2', dname.lower()):
            self.check_macs2_version()
            dname = re.sub('skip_', '', dname)
            self.dname = dname

        result_type_dict = self.params['result_types']

        self.rtd = result_type_dict

        if dname in result_type_dict:
            result_type = result_type_dict[dname]

        self.rt = result_type

    # Create output subdirectories for each Workflow result type
    def prep_output_folder(self):

        folder_dict = self.params['folders']

        if self.rt in folder_dict:
            result_folder = os.path.join(self.dir, folder_dict[self.rt])
            if hasattr(self, 'macs2v'):
                result_folder += self.macs2v

        if not os.path.isdir(result_folder) and self.state is 'active':
            os.makedirs(result_folder)

        self.folder = result_folder


    def prep_download_instructions(self):

        if not hasattr(self, 'folder'):
            self.prep_output_folder()

        instructions = {}

        ext_dict = self.params['extensions']
        method_dict = self.params['methods']

        if self.rt in ext_dict:
            extension = ext_dict[self.rt]
            if re.search('^\.', extension):
                method = method_dict[os.path.splitext(extension)[0]]
            else:
                method = method_dict[os.path.splitext(extension)[1]]
            instructions['out_file'] = os.path.join(self.folder, self.lib + extension)

            if method == 'remote':
                instructions['file_url'] = (self.gi.base_url + '/datasets/' + self.oid + '/display?to_ext=html')
            elif method == 'local':
                instructions['file_url'] = self.gi.datasets.show_dataset(self.oid)['file_name']

            instructions['method'] = method

            if 'bam' in extension:
                instructions['out_idx'] = os.path.join(self.folder, self.lib + extension + '.bai')
                instructions['idx_url'] = self.gi.datasets.show_dataset(self.oid)['metadata_bam_index']

        self.instructions = instructions


    def show(self):
        self.state = 'idle'

        if self.rt:
            if not hasattr(self, 'instructions'):
                self.prep_download_instructions()

            return {'dataset_name': self.dname,
                    'result_type': self.rt,
                    'result_folder': self.folder,
                    'instructions': self.instructions}
        else:
            return {'dataset_name': self.dname,
                    'result_type': self.rt,
                    'result_folder': 'NA',
                    'instructions': 'NA'}

    def go(self):
        self.state = 'active'

        if self.rt:
            if self.rd[self.params['folders'][self.rt]]:
                self.prep_output_folder()

                if not hasattr(self, 'instructions'):
                    self.prep_download_instructions()

                msg = DownloadHandler(self.gs, self.instructions).get_data()
            else:
                msg = ["Excluded result type; skipping."]
        else:
            msg = ["Non-requested result type; skipping."]

        return msg



###################################

class DownloadHandler(object):

    def __init__(self, galaxy_session, instructions):
        self.gs = galaxy_session
        self.src = instructions['file_url']
        self.path = instructions['out_file']
        self.method = instructions['method']

        if 'idx_url' in instructions:
            self.idx_src = instructions['idx_url']
            self.idx_path = instructions['out_idx']

    def get_data(self):
        message=[]
        if self.method == 'remote':
            message.append(("Copying file from %s to %s via remote connection." %
                            (self.src, self.path)))

            r = self.gs.get(self.src)
            with open(self.path, 'wb') as f:
                f.write(r.content)

        elif self.method == 'local':
            message.append(("Copying file from %s to %s via SLURM." %
                            (self.src, self.path)))
            os.system(('sbatch -N 1 -o slurm.out --open-mode=append <<EOF\n'
                       '#!/bin/bash\n'
                       'cp %s %s') % (self.src, self.path))

            if hasattr(self, 'idx_src'):
                message.append(("Copying index from %s to %s via SLURM." %
                                (self.idx_src, self.idx_path)))
                os.system(('sbatch -N 1 -o slurm.out --open-mode=append <<EOF\n'
                           '#!/bin/bash\n'
                           'cp %s %s') % (self.idx_src, self.idx_path))

        return message


###################################

class ResultStitcher(object):
    def __init__(self, result_type=None, processed_dir=None, lib_list=None):
        self.result_type = result_type
        self.processed_dir = processed_dir
        self.result_dir = os.path.join(self.processed_dir, self.result_type)
        self.lib_list = lib_list

        if self.lib_list is None:
            self.lib_list = self.get_lib_list(self.result_dir)

    def get_lib_id(self, lib_file):
        lib_id = re.search('lib[0-9]+(.*(XX)+)*', lib_file).group()

        return lib_id

    def get_lib_list(self, result_dir):
        self.lib_list = [self.get_lib_id(lib_file) \
                   for lib_file in os.listdir(self.result_dir) \
                   if 'lib' in lib_file]
        self.lib_list = list(set(self.lib_list))
        self.lib_list.sort()
        return self.lib_list

    def build_count_dict(self):
        self.count_dict = {}
        print("\nGenerating combined counts data...")
        for idx, lib in enumerate(self.lib_list):
            file_path = [os.path.join(self.result_dir, file_name) \
                        for file_name in os.listdir(self.result_dir) \
                        if lib in file_name][0]

            with open(file_path) as csv_file:
                reader = csv.reader(csv_file, delimiter = '\t')
                if idx == 0:
                    self.count_header = ['geneName', lib]
                    for row in reader:
                        self.count_dict[row[0]] = [row[1]]
                else:
                    self.count_header.append(lib)
                    for row in reader:
                        self.count_dict[row[0]].append(row[1])

        return (self.count_header, self.count_dict)

    def write_counts_file(self, counts_file):
        print("Writing combined counts file...")
        with open(counts_file, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(self.count_header)
            for entry in self.count_dict:
                writer.writerow([entry] + self.count_dict[entry])

    def build_metric_list(self):
        # Specify information for combined metric file below
        self.metric_header = ['lib_id']
        self.metric_list = []

        # Specify all output file_names
        ### picard align/rnaseq extensions are swapped - need to fix!!
        metric_file_dict = {'picard_align': {'file_ext': '_al.zip',
                                           'file_name': 'CollectAlignmentSummaryMetrics.metrics.txt'},
                          'picard_rnaseq': {'file_ext': '_qc.zip',
                                            'file_name': 'CollectRnaSeqMetrics.metrics.txt'},
                          'tophat_stats': {'file_ext': 'ths.txt'},
                          'htseq': {'file_ext': 'mm.txt'},
                          'picard_markdups': {'file_ext': 'MarkDups.zip',
                                              'file_name': 'MarkDuplicates.metrics.txt'},
                          'atacseq_metrics': {'file_ext': 'atac.zip',
                                              'file_name': 'MTDupsFilterStats_html.html'},
                          'fastqmcf_log': {'file_ext': '_fqmcf.txt'}}
        metric_types = ['picard_align', 'picard_rnaseq', 'tophat_stats', 'htseq', 'picard_markdups', 'atacseq_metrics', 'fastqmcf_log']

        print("\nGenerating combined metrics data...")
        for idx, lib in enumerate(self.lib_list):
            metrics = [lib]
            for metric_type in metric_types:
                file_path = [os.path.join(self.result_dir, file_name) \
                            for file_name in os.listdir(self.result_dir) \
                            if lib in file_name and
                            metric_file_dict[metric_type].get('file_ext') in file_name]

                if len(file_path):
                    file_path = file_path[0]
                else:
                    continue

                if '.zip' in metric_file_dict[metric_type].get('file_ext'):
                    with zipfile.ZipFile(file_path) as metric:
                        met_src = StringIO.StringIO(metric.read(metric_file_dict[metric_type].get('file_name')))
                        metric_lines = met_src.readlines()
                    if metric_type is not 'atacseq_metrics':
                        metric_vals = metric_lines[7].rstrip('\n').split('\t')
                        header_vals = metric_lines[6].rstrip('\n').split('\t')
                    else:
                        metric_vals = [re.search('[0-9]{2,}', l).group() for l in metric_lines]
                        metric_vals = [metric_vals[0], metric_vals[1],
                                      '%f' % (1 - float(metric_vals[1]) / float(metric_vals[0])),
                                      metric_vals[2],
                                      '%f' % (1 - float(metric_vals[2]) / float(metric_vals[0])),
                                      metric_vals[3],
                                      '%f' % (1 - float(metric_vals[3])/ float(metric_vals[2]))]
                        header_vals = ['aligned_reads', 'aligned_reads_wo_dups', 'perc_dups',
                                      'aligned_reads_wo_mito', 'perc_mito',
                                      'aligned_reads_wo_mito_wo_dups', 'perc_non_mito_dups']

                else:
                    metric_vals = []
                    if metric_type is 'tophat_stats':
                        col = 0
                        header_vals = ['fastq_total_reads', 'reads_aligned_sam',
                                   'aligned', 'reads_with_mult_align',
                                   'algn_seg_with_mult_algn']
                    elif metric_type is 'htseq':
                        col = 1
                        header_vals = ['no_feature',
                                   'ambiguous', 'too_low_aQual', 'not_aligned',
                                   'alignment_not_unique']
                    elif metric_type is 'fastqmcf_log':
                        header_vals = ['post_trim_fastq_reads']

                    if metric_type is 'fastqmcf_log':
                        with open(file_path) as metric:
                            metric_lines = metric.readlines()
                            metric_vals.append([line.strip().split(': ')[1] \
                                               for line in metric_lines \
                                               if ':' in line][-2])
                    else:
                        with open(file_path) as metric:
                            metric_lines = metric.readlines()
                            for line in metric_lines:
                                metric_vals.append(line.strip().split('\t')[col])
                if idx == 0:
                    self.metric_header = self.metric_header + header_vals
                metrics = metrics + metric_vals

            # Add column for normalized reads
            if 'fastq_total_reads' in self.metric_header:
                ure_idx = self.metric_header.index("UNPAIRED_READS_EXAMINED")
                unpaired_examined = float(metrics[ure_idx])

                ftr_idx = self.metric_header.index("fastq_total_reads")
                total_reads = float(metrics[ftr_idx])

                metrics.append("%f" % (unpaired_examined / total_reads))

                if idx == 0:
                    self.metric_header = self.metric_header + ['mapped_reads_w_dups']
            else:
                al_idx = self.metric_header.index('aligned_reads')
                aligned_reads = float(metrics[al_idx])

                ftr_idx = self.metric_header.index('post_trim_fastq_reads')
                total_reads = float(metrics[ftr_idx])

                metrics.append("%f" % (aligned_reads / total_reads))

                if idx == 0:
                    self.metric_header = self.metric_header + ['perc_post_trim_reads_aligned']

            self.metric_list.append(metrics)

        return (self.metric_header, self.metric_list)

    def write_metrics_file(self, metrics_file):
        print("Writing combined metrics file...")
        with open(metrics_file, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(self.metric_header)
            for entry in self.metric_list:
                writer.writerow(entry)

    def execute(self, target_file):
        if self.result_type is 'counts':
            self.build_count_dict()
            self.write_counts_file(target_file)
        elif self.result_type is 'metrics':
            self.build_metric_list()
            self.write_metrics_file(target_file)
        print "Done"
