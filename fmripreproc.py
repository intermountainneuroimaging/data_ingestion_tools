#!/bin/python

from pathlib import Path
import sys, subprocess, os, nipype, datetime, logging

sys.path.append('/projects/ics/software/flywheel-python/bids-client/')
sys.path.append('/projects/ics/software/flywheel-python/')
from getpass import getpass
import flywheel, flywheel_gear_toolkit
from flywheel_gear_toolkit.interfaces.command_line import (
    build_command_list,
    exec_command,
)
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive, zip_output
from utils.zip_htmls import zip_htmls
from flywheel_bids.export_bids import export_bids
from flywheel_bids.export_bids import download_bids_dir
import subprocess as sp
from datetime import datetime


def main(fw):
    # Flywheel Upload Preprocessing Dataset...

    # Upload banich fmri-preproc
    # set directories
    root_dir = '/pl/active/hutchison/studies/alcohol/AIM/aviva_Analysis'
    source_dir = 'fmripreproc'
    run_upload = False

    # help(zip_output)
    counter = 0
    project = fw.lookup('khutchison/AIM')
    analysis_name = 'fmripreproc'

    for session in project.sessions.find():
        full_session = fw.get_session(session.id)
        # clean working directory
        try:
            os.system('rm /pl/active/hutchison/studies/alcohol/AIM/aviva_Analysis/fw_uploads/pipeline*.zip')
        except:
            # clean directory
            log.debug('output directory not stored previously')
        # check if uploaded analysis already exists
        flag = True
        for analysis in full_session.analyses:
            # only print ones that match the  analysis label
            if analysis_name in analysis.label:
                flag = False

        # zip and upload files
        if flag:
            log.info('Uploading subject: %s session: %s banich-fmripreproc ', session.subject.label, session.label)
            upload_zip_analysis(full_session, root_dir, source_dir)
            counter = counter + 1
        else:
            log.info('Banich fmripreproc upload already exists subject: %s session: %s ', session.subject.label,
                     session.label)

        # if counter >10:
        #     break


def upload_zip_analysis(session_object, root_dir, source_dir):
    subject = session_object.subject.label
    session = session_object.label

    if not os.path.exists(root_dir + '/fw_uploads/' + "pipeline_outputs.zip") and os.path.exists(
            root_dir + '/' + source_dir + '/' + subject + '/' + session):
        run_upload = True
    else:
        run_upload = False

    if run_upload:
        # zip output except for scratch
        log.info('Zipping contents of directory %s', root_dir + '/' + source_dir + '/' + subject + '/' + session)
        zip_output(root_dir, source_dir + '/' + subject + '/' + session, "fw_uploads/pipeline_outputs.zip",
                   exclude_files=['scratch'])

        # zip logs
        log.info('Zipping logs %s', root_dir + '/' + source_dir + '/' + subject + '/' + session)
        zip_output(root_dir, source_dir + '/logs/' + subject, "fw_uploads/pipeline_logs.zip", exclude_files=['scratch'])

        # zip scripts (same for all sessions)
        if not os.path.exists(root_dir + '/fw_uploads/run_scripts.zip'):
            zip_output(root_dir, "scripts/flywheel_scripts", "fw_uploads/run_scripts.zip", exclude_files=['scratch'])

        # create an analysis for that session
        timestamp = os.path.getmtime(root_dir + '/' + source_dir + '/' + subject + '/' + session)
        dtobject = datetime.fromtimestamp(timestamp)
        analysis = session_object.add_analysis(label='banich_fmripreproc' + dtobject.strftime(" %x %X"))
        log.info('Creating analysis %s', 'banich_fmripreproc' + dtobject.strftime(" %x %X"))

        # log size of uploads
        duResults = sp.Popen(
            "du -hs " + root_dir + '/fw_uploads/*', shell=True, stdout=sp.PIPE, stderr=sp.PIPE, universal_newlines=True
        )
        stdout, _ = duResults.communicate()
        log.info("\n %s", stdout)

        # loop through all files to upload
        for filename in sorted(os.listdir(root_dir + '/fw_uploads/')):
            file_out = os.path.join(root_dir, "fw_uploads", filename)

            # checking if it is a file
            if os.path.isfile(file_out):
                log.info('Uploading %s', file_out)
                # upload output file to analysis container
                analysis.upload_output(file_out)

    else:
        if os.path.exists(root_dir + '/fw_uploads/' + "pipeline_outputs.zip"):
            log.info('Output zipped file already exists')
        if not os.path.exists(root_dir + '/' + source_dir + '/sub-' + subject + '/ses-' + session):
            log.info('Directory path selected for output zip does not exist')


def zip_logs(logsdir, logname, outdir):
    # 1. analysis_configuration: stored in output log
    print("cp " + logsdir + "/" + logname + ".o0000 " + outdir + "/analysis_configuration.txt")
    print("cp " + logsdir + "/" + logname + "_info.log " + outdir + "/analysis_information.txt")
    print("cp " + logsdir + "/" + logname + ".e0000 " + outdir + "/analysis_logs_errors.txt")

    os.system("cp " + logsdir + "/" + logname + ".o0000 " + outdir + "/analysis_configuration.txt")
    os.system("cp " + logsdir + "/" + logname + "_info.log " + outdir + "/analysis_information.txt")
    os.system("cp " + logsdir + "/" + logname + ".e0000 " + outdir + "/analysis_logs_errors.txt")
    os.system("cp " + logsdir + "/" + logname + "_run.sh " + outdir + "/run.sh")


# Only execute if file is run as main, not when imported by another module
if __name__ == "__main__":
    # Instantiate a logger
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    log = logging.getLogger('root')

    # Create client, using CLI credentials
    fw = flywheel.Client()

    # who am I logged in as?
    log.info('You are now logged in as %s to %s', fw.get_current_user()['email'], fw.get_config()['site']['api_url'])

    main(fw)

