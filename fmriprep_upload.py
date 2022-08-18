#!/usr/bin/env python
"""The run script."""
# Import packages
from getpass import getpass
from pathlib import Path
import os, sys
import logging

import pandas as pd
import flywheel
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive, zip_output
from datetime import datetime as dt
import argparse
from functools import partial
import subprocess as sp
import glob

# contains all functions specific to fmriprep flywheel uploads
from utils.utils import get_project_id, analysis_exists, zip_htmls

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# set version
__version__ = "0.0.1"


# define functions here...

def parser(context):
    # parse inputs similarly to cli ingest bids function

    def _path_exists(path, parser):
        """Ensure a given path exists."""
        if path is None or not Path(path).exists():
            raise parser.error(f"Path does not exist: <{path}>.")
        return Path(path).absolute()

    def _is_file(path, parser):
        """Ensure a given path exists and it is a file."""
        path = _path_exists(path, parser)
        if not path.is_file():
            raise parser.error(f"Path should point to a file (or symlink of file): <{path}>.")
        return path

    parser = argparse.ArgumentParser(
        description="Add description here",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    PathExists = partial(_path_exists, parser=parser)
    IsFile = partial(_is_file, parser=parser)

    ##########################
    #   Required Arguments   #
    ##########################
    parser.add_argument(
        "SRC",
        action="store",
        metavar="PATH",
        type=PathExists,
        help="path to fmriprep derivative folder"
    )
    parser.add_argument("group", help="group id to locate flywheel target (case sensitive)")
    parser.add_argument("project", help="project id to locate flywheel target (case sensitive)")

    ##########################
    #   Optional Arguments   #
    ##########################
    parser.add_argument(
        "--subject",
        action='store',
        help="Upload fmriprep analysis for specified subject (e.g. sub-01)")
    parser.add_argument(
        "--session",
        action='store',
        help="Upload fmriprep analysis for specified session. This must be used in combination with subject flag (e.g. ses-01)")
    parser.add_argument(
        "--log-path",
        action="store",
        metavar="PATH",
        type=PathExists,
        help="specify path to log file or directory, otherwise check for logs in root directory"
    )
    parser.add_argument(
        "--scripts-path",
        action="store",
        metavar="PATH",
        type=PathExists,
        help="specify path to run_script file or directory, otherwise check for scripts in root directory"
    )
    parser.add_argument(
        "--allow-multiples",
        action="store_true",
        help="ignore check for previously created fmriprep analyses in flywheel session",
    )
    parser.add_argument("-v", "--verbosity", action="count", default=0)

    args = parser.parse_args()

    if args.session and (args.subject is None):
        parser.error("--session must be defined with --subject")

    # add all args to context
    args_dict = args.__dict__
    context.update(args_dict)

    ##########################
    #    Argument Checks     #
    ##########################

    # project and group exist in flywheel (needed later for fw.lookup())
    project_id = get_project_id(context['fw'], args.project)
    if project_id:
        # check correct group assignment
        project = context['fw'].get_project(project_id)
        if not project.group == args.group:
            parser.error("No group and project match found in " + context['fw'].get_config()['site']['api_url'])
    else:
        parser.error("No group and project match found in " + context['fw'].get_config()['site']['api_url'])

    # check necessary upload files exist
    if not args.log_path:
        context['log_path'] = os.path.join(args.SRC, 'logs')

    if not args.scripts_path:
        context['scripts_path'] = os.path.join(args.SRC, 'scripts')

    checklist = [context['log_path'],
                 context['scripts_path'],
                 os.path.join(context['SRC'], 'analysis_configuration.txt'),
                 os.path.join(context['SRC'], 'analysis_information.txt'),
                 ]

    for f in checklist:
        if not os.path.exists(f):
            parser.error("Missing required input file or directory: " + f)

    # if all checks pass - fix all paths to be absolute
    context['SRC'] = os.path.abspath(context['SRC'])
    context['log_path'] = os.path.abspath(context['log_path'])
    context['scripts_path'] = os.path.abspath(context['scripts_path'])

    # pull analysis derivative path
    if context['subject'] and context['session']:
        subj = context['subject'].strip('sub-')
        ses = context['session'].strip('ses-')
        bidspath = os.path.join(context['SRC'], 'sub-' + subj, 'ses-' + ses)
        context['run_level'] = 'session'
    elif context['subject'] and not context['session']:
        subj = context['subject'].strip('sub-')
        bidspath = os.path.join(context['SRC'], 'sub-' + subj)
        context['run_level'] = 'subject'
    else:
        parser.error('Unknown subject and session configuration')

    if os.path.exists(bidspath):
        context['bidspath'] = bidspath
    else:
        parser.error('Fmriprep derivatives dataset not present: ' + bidspath)

    # end parser


def main(context):
    """Entry point."""

    # parse user inputs and store in context
    parser(context)

    # print all files (and file sizes for zip and upload)
    data_tree(context['SRC'], os.path.join(context['SRC'], 'data_tree.txt'))

    # check if conditions are met for upload (any duplicates?)
    analysis_name = 'fmriprep'
    fw = context['fw']
    if context['run_level'] == 'session':
        ctn = fw.lookup(
            context['group'] + '/' + context['project'] + '/' + context['subject'] + '/' + context['session'])
        session = fw.get_session(ctn.id)
        if analysis_exists(session, analysis_name) and not context['allow_multiples']:
            log.exception('Analysis already exists in flywheel container: %s', ctn.id)
            sys.exit(1)

    elif context['run_level'] == 'subject':
        ctn = fw.lookup(context['group'] + '/' + context['project'] + '/' + context['subject'])
        subject = fw.get_subject(ctn.id)
        if analysis_exists(subject, analysis_name) and not context.allow_multiples:
            log.exception('Analysis already exists in flywheel container: %s', ctn.id)
            sys.exit(1)

    # begin analysis upload!
    print('starting upload')
    upload_analysis(context)

    # check outputs
    # ...


def generate_analysis_info(cmd):
    Results = sp.Popen(
        cmd + " -h", shell=True, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
    )
    stdout, _ = Results.communicate()
    log.info("\n %s", stdout)
    file = open("analysis_information.txt", "w")
    file.write(stdout)
    file.close()


def generate_analysis_config():
    log.info("Function under active development. Come back later!!")


def upload_analysis(context):
    fw = context['fw']

    # set container for upload (subject or session)
    if context['run_level'] == 'session':
        ctn = fw.lookup(
            context['group'] + '/' + context['project'] + '/' + context['subject'] + '/' + context['session'])
        fw_container = fw.get_session(ctn.id)
    elif context['run_level'] == 'subject':
        ctn = fw.lookup(context['group'] + '/' + context['project'] + '/' + context['subject'])
        fw_container = fw.get_subject(ctn.id)

    try:
        # create temporary upload location
        os.system('mkdir -p ' + os.path.join(context['SRC'], 'tmp_upload'))

        # zip fmriprep results except for scratch
        log.info('Zipping contents of directory %s', context['bidspath'])
        relpath = os.path.relpath(context['bidspath'], context['SRC'])
        zip_output(context['SRC'], relpath, os.path.join(context['SRC'], 'tmp_upload', 'bids-fmriprep.zip'),
                   exclude_files=['scratch'])

        # zip logs
        log.info('Zipping logs %s', context['log_path'])
        if os.path.isdir(context['log_path']):
            # TODO - currently treat log path as only containing relevant log info. I need to develop a sort or filter method!
            relpath = os.path.relpath(context['log_path'], context['SRC'])
            zip_output(context['SRC'], relpath, os.path.join(context['SRC'], 'tmp_upload', 'logs.zip'))
        else:
            os.system('cp ' + context['log_path'] + ' ' + os.path.join(context['SRC'], 'tmp_upload'))

        # zip scripts
        log.info('Zipping scripts %s', context['scripts_path'])
        if os.path.isdir(context['scripts_path']):
            relpath = os.path.relpath(context['scripts_path'], context['SRC'])
            zip_output(context['SRC'], relpath, os.path.join(context['SRC'], 'tmp_upload', 'run_scripts.zip'))
        else:
            os.system('cp ' + context['scripts_path'] + ' ' + os.path.join(context['SRC'], 'tmp_upload'))

        # copy metadata files to upload directory
        os.system(
            'cp ' + os.path.join(context['SRC'], 'analysis_configuration.txt') + ' ' + os.path.join(context['SRC'],
                                                                                                    'tmp_upload'))
        os.system('cp ' + os.path.join(context['SRC'], 'analysis_information.txt') + ' ' + os.path.join(context['SRC'],
                                                                                                        'tmp_upload'))

        # add directory description:
        data_tree(context['bidspath'], os.path.join(context['SRC'], 'tmp_upload/data_tree.txt'))

        # create an analysis for that session
        analysis = fw_container.add_analysis(label='bids-fmriprep: Upload ' + dt.now().strftime(" %x %X"))
        log.info('Creating %s analysis %s', context['run_level'], 'bids-fmriprep ' + dt.now().strftime(" %x %X"))

        # log size of uploads
        duResults = sp.Popen(
            "du -hs " + os.path.join(context['SRC'], 'tmp_upload'), shell=True, stdout=sp.PIPE, stderr=sp.PIPE,
            universal_newlines=True
        )
        stdout, _ = duResults.communicate()
        log.info("\n %s", stdout)

        # loop through all files to upload
        for filename in sorted(os.listdir(os.path.join(context['SRC'], 'tmp_upload'))):
            file_out = os.path.join(context['SRC'], 'tmp_upload', filename)

            # checking if it is a file
            if os.path.isfile(file_out):
                log.info('Uploading %s', file_out)
                # upload output file to analysis container
                analysis.upload_output(file_out)

        # check upload!
        check_upload_size(analysis, os.path.join(context['SRC'], 'tmp_upload'))
    except Exception as e:
        log.error(e)
    finally:
        os.system('rm -Rf ' + os.path.join(context['SRC'], 'tmp_upload'))


def data_tree(startpath, filename):
    file = open(filename, "w")

    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level - 1)
        file.write('{}{}/\n'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level) + '|----'
        for f in files:
            duResults = sp.Popen(
                "du -hs " + os.path.join(root, f), shell=True, stdout=sp.PIPE, stderr=sp.PIPE,
                universal_newlines=True
            )
            stdout, _ = duResults.communicate()
            flsize = stdout.split('\t')[0]
            if not f == 'data_tree.txt':
                file.write('{}{}\t{}\n'.format(subindent, f, flsize))

    duResults = sp.Popen(
        "du -hs " + startpath, shell=True, stdout=sp.PIPE, stderr=sp.PIPE,
        universal_newlines=True
    )
    stdout, _ = duResults.communicate()
    flsize = stdout.split('\t')[0]
    file.write('{} {}\n'.format('Total Directory Size: ', flsize))
    file.close()


def check_upload_size(analysis_container, source_dir):
    log.info("Function under active development. Come back later!!")


def check_checksum(analysis_container, source_dir):
    log.info("Function under active development. Come back later!!")


def cleanup():
    log.info("Function under active development. Come back later!!")


# Only execute if file is run as main, not when imported by another module
if __name__ == "__main__":  # pragma: no cover

    pycontext = dict()

    # Create client, using CLI credentials
    pycontext['fw'] = flywheel.Client()

    # who am I logged in as?
    log.info('You are now logged in as %s to %s', pycontext['fw'].get_current_user()['email'],
             pycontext['fw'].get_config()['site']['api_url'])

    main(pycontext)
    # 1. parse inputs (perform necessary checks, eg path exists, sub / ses exist)

    # 2. check upload level (project, subject, session)

    #    2a. ignore project level for now (return error)
    #    2b. subject/session level -> run.py?

    # run.py
    # pull correct flywheel session
    # check if analysis exists -- if so look for "allow-multiples" (error if allow-multiples = false)
    # look for logs, analysis_configuration.txt, analysis_information.txt, run_script[.sh,.zip]
    # if any not present, fail
    # set (and check) basepath, fmiprep_zip_path, temp_uploads path

    # run zipping for output folder (and logs if necessary)
    # zip report html
    # create new analysis and upload all files
    # check upload sucsess (checksum - TODO, datasize)
