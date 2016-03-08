import datetime

from bripipetools.util import string_ops as so

### file/path/string parsing functions ###

def get_lib_id(lib_str):
    lib_id = so.matchdefault('lib[1-9]+[0-9]*', lib_str)

    return lib_id

def parse_fc_run_id(fc_run_id):
    fc_parts = fc_run_id.split('_')

    d = datetime.datetime.strptime(fc_parts[0], '%y%m%d')

    date = datetime.date.isoformat(d)
    instrument_id = fc_parts[1]
    run_num = int(fc_parts[2])

    fc_id = so.matchdefault('(?<=(_(A|B|D)))([A-Z]|[0-9])*XX', fc_run_id)
    fc_pos = so.matchdefault('.{1}(?=%s)' % fc_id, fc_run_id)

    return date, instrument_id, run_num, fc_id, fc_pos

def get_proj_id(proj_str):
    proj = so.matchdefault('P+[0-9]+(-[0-9]+){,1}', proj_str)
    proj_id = int(so.matchdefault('(?<=P)[0-9]+', proj))
    subproj_id = int(so.matchdefault('(?<=-)[0-9]+', proj))

    return proj_id, subproj_id

def get_fastq_source(file_path):
    lane_id = so.matchdefault('(?<=_)L00[1-8]', file_path)
    read_id = so.matchdefault('(?<=_)R[1-2]', file_path)
    sample_num = int(so.matchdefault('(?<=_S)[0-9]+', file_path))
    
    return lane_id, read_id, sample_num