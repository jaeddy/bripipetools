import logging
from logging.config import fileConfig
import os
import re
import sys

import click

import bripipetools


config_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'config'
)
fileConfig(os.path.join(config_path, 'logging_config.ini'),
           disable_existing_loggers=False)
logger = logging.getLogger()
logger.info("Starting `bripipetools`")
DB = bripipetools.genlims.connect()
RB = bripipetools.researchdb.connect()

def get_workflow_batches(flowcell_path, all_workflows=False):
    """
    List the workflow batch files for a flowcell run.
    """
    submissions = os.path.join(flowcell_path, 'globus_batch_submission')
    return (os.path.join(submissions, wb)
            for wb in os.listdir(submissions)
            if ('optimized' in wb or all_workflows))


def get_processed_projects(flowcell_path):
    """
    List processed projects for a flowcell run.
    """
    return (os.path.join(flowcell_path, pp)
            for pp in os.listdir(flowcell_path)
            if re.search('Project_.*Processed', pp))


def postprocess_project(output_type, exclude_types, stitch_only, clean_outputs,
                        project_path):
    """
    Execute postprocessing steps (e.g., stitching, compiling, cleaning)
    on outputs in a processed project folder.
    """
    project_path_short = os.path.basename(os.path.normpath(project_path))
    if clean_outputs:
        bripipetools.postprocessing.OutputCleaner(project_path).clean_outputs()
        logger.info("Output files cleaned for '{}".format(project_path_short))

    combined_paths = []
    if output_type in ['c', 'a'] and 'c' not in exclude_types:
        logger.debug("generating combined counts file")
        path = os.path.join(project_path, 'counts')
        # Determine whether the path exists before calling write_table
        # important for eg: ChIPseq, which doesn't contain a 'counts' folder.
        if not os.path.exists(path):
            proceed = raw_input("{} not found & will be skipped. Proceed? (y/[n]): "
                                .format(path))
            if proceed != 'y':
                logger.info("Exiting program.")
                sys.exit(1)
        else:
            bripipetools.postprocessing.OutputStitcher(path).write_table()

    if output_type in ['m', 'a'] and 'm' not in exclude_types:
        logger.debug("generating combined metrics file")
        path = os.path.join(project_path, 'metrics')
        combined_paths.append(
            bripipetools.postprocessing.OutputStitcher(path).write_table())

    if output_type in ['q', 'a'] and 'q' not in exclude_types:
        logger.debug("generating combined QC file(s)")
        path = os.path.join(project_path, 'QC')
        bripipetools.postprocessing.OutputStitcher(
            path).write_overrepresented_seq_table()
        combined_paths.append(
            bripipetools.postprocessing.OutputStitcher(path).write_table())

    if output_type in ['v', 'a'] and 'v' not in exclude_types:
        logger.debug("generating combined validation file(s)")
        path = os.path.join(project_path, 'validation')
    try:
        combined_paths.append(
            bripipetools.postprocessing.OutputStitcher(path).write_table()
        )
    except OSError:
        logger.warn(("no validation files found "
                     "for project {}; skiproject_pathing")
                    .format(project_path))
    logger.info("Combined output files generated for '{}' with option '{}'"
                .format(project_path_short, output_type))

    if not stitch_only:
        bripipetools.postprocessing.OutputCompiler(combined_paths).write_table()
        logger.info("Merged all combined summary data tables for '{}'"
                    .format(project_path_short))

@click.group()
@click.option('--quiet', 'verbosity', flag_value='quiet',
              help=("only display printed outputs in the console - "
                    "i.e., no log messages"))
@click.option('--debug', 'verbosity', flag_value='debug',
              help="include all debug log messages in the console")
def main(verbosity):
    """
    Command line interface for the `bripipetools` library.
    """
    if verbosity == 'quiet':
        logger.setLevel(logging.ERROR)
    elif verbosity == 'debug':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


@main.command()
@click.option('--endpoint', default='benaroyaresearch#BRIGridFTP',
              help=("Globus Online endpoint where input data is stored "
                    "and outputs will be saved"))
@click.option('--workflow-dir', default='/mnt/genomics/galaxy_workflows',
              help=("path to folder containing Galaxy workflow template "
                    "files to be used for batch processing"))
@click.option('--all-workflows/--optimized-only', default=False,
              help=("indicate whether to include all detected workflows "
                    "as options or to keep 'optimized' workflows only"))
@click.option('--sort-samples', '-s', is_flag=True,
              help=("sort samples from smallest to largest (based on total "
                    "size of raw data files) before submitting; this is most "
                    "useful when also restricting the number of samples"))
@click.option('--num-samples', '-n', default=None, type=int,
              help=("restrict the number of samples submitted for each "
                    "project on the flowcell"))
@click.option('--manifest', '-m', is_flag=True,
              help=("indicates that input path is a manifest of sample "
                    "or folder paths (not a flowcell run) from which "
                    "a workflow batch is to be created (note: options "
                    "'sort-samples' and 'num-samples' will be ignored)"))
@click.option('--out-dir', '-o', default=os.path.curdir,
              help=("for input manifest, folder where outputs are to "
                    "be saved; default is current directory"))
@click.option('--tag', '-t', default='',
              help=("for custom sample submissions, tag for labelling "
                    "processed outputs"))
@click.argument('path')
def submit(endpoint, workflow_dir, all_workflows, sort_samples, num_samples,
           manifest, out_dir, tag, path):
    """
    Prepare batch submission for unaligned samples from a flowcell run
    or from a list of paths in a manifest file.
    """
    if not manifest:
        logger.info("Creating batches for unaligned samples and projects "
                    "from flowcell run '{}'".format(path))
        logger.info("... will search '{}' for workflow template options"
                    .format(workflow_dir))
        logger.info("... destination endpoint for processing outputs is '{}'"
                    .format(endpoint))
        submitter = bripipetools.submission.FlowcellSubmissionBuilder(
            path=path,
            endpoint=endpoint,
            db=DB,
            workflow_dir=workflow_dir,
            all_workflows=all_workflows
        )
        submit_paths = submitter.run(sort=sort_samples,
                                     num_samples=num_samples)
    else:
        logger.info("Creating batche unaligned samples listed in '{}'"
                    .format(path))
        logger.info("... will search '{}' for workflow template options"
                    .format(workflow_dir))
        logger.info("... destination endpoint for processing outputs is '{}'"
                    .format(endpoint))
        logger.info("... outputs to be saved in '{}'"
                    .format(out_dir))
        submitter = bripipetools.submission.SampleSubmissionBuilder(
            manifest=path,
            out_dir=out_dir,
            endpoint=endpoint,
            workflow_dir=workflow_dir,
            all_workflows=all_workflows,
            tag=tag
        )
        submit_paths = submitter.run()

    print("\nPrepared the following workflow batch submit files:\n"
          "(ready for upload to Globus Genomics)\n")
    for p in submit_paths:
        print(bripipetools.util.swap_root(p, 'genomics', '/mnt/'))


@main.command()
@click.option('--sexmodel', default='y_sq_over_tot',
              help=("The model for determining the gender based on "
                "X and Y chromosome reads. Possible options are:\n"
                "\'y_sq_over_tot\': y_counts^2 / total_counts\n"
                "\'gene_ratio\': y_genes / x_genes\n"
                "\'counts_ratio\': y_counts / x_counts"))
@click.option('--sexcutoff', default=0.5,
              help=("The cutoff for the sexmodel, where 'M' is the "
                "prediction for a sexmodel value greater than cutoff"))
@click.option('--workflow-dir', default='/mnt/genomics/galaxy_workflows',
              help=("path to folder containing .ga Galaxy workflow "
                    "files to be used for batch processing"))
@click.argument('path')
def dbify(sexmodel, sexcutoff, workflow_dir, path):
    """
    Import data from a flowcell run or workflow processing batch into
    GenLIMS database.
    """
    logger.info("Importing data to '{}' based on path '{}'"
                .format(DB.name, path))
    importer = bripipetools.dbification.ImportManager(
        path=path,
        db=DB,
        run_opts = {"sexmodel":sexmodel, 
                    "sexcutoff":sexcutoff,
                    "workflow_dir":workflow_dir}
    )
    importer.run(collections='all')
    logger.info("Import complete.")

@main.command()
@click.option('--sexmodel', default='y_sq_over_tot',
              help=("The model for determining the gender based on "
                "X and Y chromosome reads. Possible options are:\n"
                "\'y_sq_over_tot\': y_counts^2 / total_counts\n"
                "\'gene_ratio\': y_genes / x_genes\n"
                "\'counts_ratio\': y_counts / x_counts"))
@click.option('--sexcutoff', default=0.5,
              help=("The cutoff for the sexmodel, where male is the "
                "prediction for a sexmodel value greater than cutoff"))
@click.argument('path')
def qc(sexmodel, sexcutoff, path):
    """
    Run quality control analyses on a target project specified by a
    workflow batch file. Note that this does not update the database,
    unlike running dbify on a workflow batch file.
    """
    logger.info("Running quality control on project based on path ''{}''"
                .format(path))
    path_items = bripipetools.parsing.parse_batch_file_path(path)
    annotator = bripipetools.annotation.WorkflowBatchAnnotator(
        workflowbatch_file=path,
        genomics_root=path_items['genomics_root'],
        db = DB,
        run_opts = {"sexmodel":sexmodel, "sexcutoff":sexcutoff}
    ).get_processed_libraries(qc=True)

@main.command()
@click.argument('path')
def researchdb(path):
    """
    Push library results to research database
    """
    logger.info("Research Database Name: {} based on path {}".format(RB.name, path))
    importer = bripipetools.dbification.ImportManager(
        path=path,
        db=RB,
        run_opts=None
    )
    importer.run(collections='researchdb')
    logger.info("Import complete.")

@main.command()
@click.option('--output-type', '-t', default='a',
              type=click.Choice(['c', 'm', 'q', 'v', 'a']),
              help=("type of output file to combine: "
                    "c [counts], m [metrics], q [qc], "
                    "v [validation], a [all]"))
@click.option('--exclude-types', '-x', multiple=True,
              type=click.Choice(['c', 'm', 'q', 'v']),
              help=("type of output file to exclude: "
                    "c [counts], m [metrics], q [qc], "
                    "v [validation]"))
@click.option('--stitch-only/--stitch-and-compile', default=False,
              help=("Do NOT compile and merge all summary "
                    "(non-count) data into a single file at "
                    "the project level"))
@click.option('--clean-outputs/--outputs-as-is', default=False,
              help="Attempt to clean/organize output files")
@click.option('--all-workflows/--optimized-only', default=False,
              help=("indicate whether to include all detected workflows "
                    "as options or to keep 'optimized' workflows only"))
@click.argument('path')
def postprocess(output_type, exclude_types, stitch_only, clean_outputs, 
                all_workflows, path):
    """
    Perform postprocessing operations on outputs of a workflow batch.
    """
    
    # Find all workflow batch files for a given project
    project_id = bripipetools.parsing.get_project_label(path)
    
    print project_id
    flowcell_dir = os.path.abspath(os.path.join(path, '..'))
    
    workflow_batches =  list(wb for wb in 
                            list(get_workflow_batches(flowcell_dir, all_workflows))
                            if project_id in wb)
    
    logger.debug("found the following workflow batches: {}"
                 .format(workflow_batches))
                 
    # check outputs of workflow batches
    genomics_root = bripipetools.util.matchdefault('.*(?=genomics)', path)
    problem_count = 0
    for wb in workflow_batches:
        logger.debug("checking outputs for workflow batch in file '{}'"
                     .format(wb))
        wb_outputs = bripipetools.monitoring.WorkflowBatchMonitor(
            workflowbatch_file=wb, genomics_root=genomics_root
        ).check_project_outputs(project_id)

        problem_outputs = filter(lambda x: x[1]['status'] != 'ok',
                                 wb_outputs.items())
        problem_count += len(problem_outputs)
        if len(problem_outputs):
            output_warnings = map(lambda x: 'OUTPUT {}: {}'.format(
                x[1]['status'].upper(), x[0]
            ), problem_outputs)
            for w in output_warnings:
                logger.warning(w)

    # give option to continue
    if problem_count > 0:
        proceed = raw_input("{} problems encountered; proceed? (y/[n]): "
                            .format(problem_count))
        if proceed != 'y':
            logger.info("Exiting program.")
            sys.exit(1)
    else:
        logger.info("No problem outputs found with any workflow batches.")
    
    postprocess_project(output_type, exclude_types, stitch_only,
                        clean_outputs, path)


@main.command()
@click.option('--output-type', '-t', default='a',
              type=click.Choice(['c', 'm', 'q', 'v', 'a']),
              help=("type of output file to combine: "
                    "c [counts], m [metrics], q [qc], "
                    "v [validation], a [all]"))
@click.option('--exclude-types', '-x', multiple=True,
              type=click.Choice(['c', 'm', 'q', 'v']),
              help=("type of output file to exclude: "
                    "c [counts], m [metrics], q [qc], "
                    "v [validation]"))
@click.option('--stitch-only/--stitch-and-compile', default=False,
              help=("Do NOT compile and merge all summary "
                    "(non-count) data into a single file at "
                    "the project level"))
@click.option('--clean-outputs/--outputs-as-is', default=False,
              help="Attempt to clean/organize output files")
@click.option('--sexmodel', default='y_sq_over_tot',
              help=("The model for determining the gender based on "
                "X and Y chromosome reads. Possible options are:\n"
                "\'y_sq_over_tot\': y_counts^2 / total_counts\n"
                "\'gene_ratio\': y_genes / x_genes\n"
                "\'counts_ratio\': y_counts / x_counts"))
@click.option('--sexcutoff', default=0.5,
              help=("The cutoff for the sexmodel, where 'M' is the "
                "prediction for a sexmodel value greater than cutoff"))
@click.option('--all-workflows/--optimized-only', default=False,
              help=("indicate whether to include all detected workflows "
                    "as options or to keep 'optimized' workflows only"))
@click.option('--workflow-dir', default='/mnt/genomics/galaxy_workflows',
              help=("path to folder containing .ga Galaxy workflow "
                    "files to be used for batch processing"))
@click.option('--database', default='all',
              help=("Database to contain sample information. Options are:\n"
              "\'researchdb\'\n\'genlims\'\n\'all\'\n\'none\'"))
@click.argument('path')
def wrapup(output_type, exclude_types, stitch_only, clean_outputs, sexmodel, 
           sexcutoff, all_workflows, workflow_dir, database, path):
    """
    Perform 'dbification' and 'postprocessing' operations on all projects and
    workflow batches from a flowcell run.
    """
    # import flowcell run details and raw data for sequenced libraries
    logger.info("Importing raw data for flowcell at path '{}'"
                .format(path))
    importer = bripipetools.dbification.ImportManager(
        path=path,
        db=DB,
        run_opts = {"sexmodel":sexmodel, 
                "sexcutoff":sexcutoff}
    )
    importer.run(collections='all')
    logger.info("Flowcell run import complete.")

    workflow_batches = list(get_workflow_batches(path, all_workflows))
    # If non-optimized workflows were used, the all-workflows flag is 
    # necessary to get, eg: sexcheck information.
    if len(workflow_batches) == 0:
        proceed = raw_input("No workflow batches detected.\n"
                            "Did you mean to use the '--all-workflows' tag?\n"
                            "Further processing may not include all data.\n"
                            "Continue processing? (y/[n]): ")
        if proceed != 'y':
            logger.info("Exiting program.")
            sys.exit(1)
    else:
        logger.debug("found the following workflow batches: {}"
                     .format(workflow_batches))

    # check outputs of workflow batches
    genomics_root = bripipetools.util.matchdefault('.*(?=genomics)', path)
    problem_count = 0
    for wb in workflow_batches:
        logger.debug("checking outputs for workflow batch in file '{}'"
                     .format(wb))
        wb_outputs = bripipetools.monitoring.WorkflowBatchMonitor(
            workflowbatch_file=wb, genomics_root=genomics_root
        ).check_outputs()

        problem_outputs = filter(lambda x: x[1]['status'] != 'ok',
                                 wb_outputs.items())
        problem_count += len(problem_outputs)
        if len(problem_outputs):
            output_warnings = map(lambda x: 'OUTPUT {}: {}'.format(
                x[1]['status'].upper(), x[0]
            ), problem_outputs)
            for w in output_warnings:
                logger.warning(w)

    # give option to continue
    if problem_count > 0:
        proceed = raw_input("{} problems encountered; proceed? (y/[n]): "
                            .format(problem_count))
        if proceed != 'y':
            logger.info("Exiting program.")
            sys.exit(1)
    else:
        logger.info("No problem outputs found with any workflow batches.")
        
    # Push info into ResDB                        
    if (database in ['researchdb', 'all']):
        logger.debug("Importing data into Research Database: {}".
            format(RB.name))
        bripipetools.dbification.ImportManager(
            path=path,
            db=RB,
            run_opts = {"sexmodel":sexmodel, 
                        "sexcutoff":sexcutoff}
        ).run(collections='researchdb')
        logger.info("Research Database import complete.")

    # import workflow batch details and data for processed libraries
    for wb in workflow_batches:
        logger.debug(
            "importing processed data for workflow batch in file '{}'"
            .format(wb)
        )
        if (database in ['genlims', 'all']):
            logger.debug("Importing data into GenLIMS Database: {}".
                format(DB.name))
            bripipetools.dbification.ImportManager(
                path=wb,
                db=DB,
                run_opts = {"sexmodel":sexmodel, 
                            "sexcutoff":sexcutoff,
                            "workflow_dir": workflow_dir}
            ).run()
            logger.info("Workflow batch import for '{}' complete."
                        .format(os.path.basename(wb)))
        #                 
        # if (database in ['researchdb', 'all']):
        #     logger.debug("Importing data into Research Database: {}".
        #         format(RB.name))
        #     importer = bripipetools.dbification.ImportManager(
        #         path=path,
        #         db=RB,
        #         run_opts = {"sexmodel":sexmodel, 
        #                     "sexcutoff":sexcutoff,
        #                     "workflow_dir": workflow_dir}
        #     )
        #     importer.run(collections='researchdb')
        #     logger.info("Workflow batch import for '{}' complete."
        #                 .format(os.path.basename(wb)))

    processed_projects = list(get_processed_projects(path))
    logger.debug("found the following processed projects: {}"
                 .format(processed_projects))

    # post-process project files
    logger.info("Postprocessing flowcell projects.")
    for pp in processed_projects:
        postprocess_project(output_type, exclude_types, stitch_only,
                            clean_outputs, pp)
    logger.info("Project postprocessing complete.")

if __name__ == "__main__":
    main()
