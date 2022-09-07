def get_project_id(fw, project_label):
    """Return the first project ID matching project_label

    Args:
       fw (flywheel.Client): A flywheel client
       project_label (str):  A Project label

    Returns:
       (str): Project ID or None if no project found
    """
    project = fw.projects.find_first(f'label={project_label}')
    if project:
        return project.id
    else:
        return None


def analysis_exists(fw_container, analysis_name, exclude_list=[]):
    # Returns True if analysis already exists with a running or complete status, else false
    # make sure to pass full session object (use fw.get_session(session.id))
    #
    # Get all analyses for the session
    flag = False
    for analysis in fw_container.analyses:
        # only print ones that match the  analysis label
        if analysis_name in analysis.label:
            # filter for only successful job
            analysis_job = analysis.job
            if not hasattr(analysis_job, 'state'):
                flag = True
            else:
                if any(analysis_job.state in string for string in ["complete", "running", "pending"]):
                    if analysis_job.failure_reason is None:
                        flag = True

        # check if session is in exclude list
        if any(fw_container.id in string for string in exclude_list):
            flag = True

    return flag


"""Compress HTML files."""

import datetime
import glob
import logging
import os
import subprocess as sp
from pathlib import Path
from bs4 import BeautifulSoup
import shutil


# FWV0 = Path.cwd()
# log = logging.getLogger(__name__)


def set_relative_hyperlinks(landing_html, relpath=os.curdir):
    """
    Removes all absolute paths for reference html files in landing_html.
    Used so that html group can be moved to different file locations easily.

    NOTE: function operates and overwrites original html!

    Args:
        landing_html: target html file
        relpath: relative path for local html references,
                        defaults to current working directory

    Returns:
        writes updated html with relative paths
    """
    data = landing_html  # html file location

    # load the file
    with open(data) as inf:
        txt = inf.read()
    soup = BeautifulSoup(txt, 'html.parser')

    # Find the elements in the file and alter path so its relative
    ref_htmls = []
    for a in soup.find_all('a'):

        if ".html" in a['href'] and os.path.exists(a['href']):
            abspath = Path(a['href'])
            ref_htmls.append(abspath)
            a['href'] = os.path.relpath(abspath, start=relpath)
        else:
            logging.info("Unable to find file: %s", a['href'])

    # save the file again
    with open(data, "w") as outf:
        outf.write(str(soup))

    return ref_htmls


def zip_it_zip_it_good(output_dir, destination_id, name, path, include_ref_htmls=False):
    """Compress html file into an appropriately named archive file *.html.zip
    files are automatically shown in another tab in the browser. These are
    saved at the top level of the output folder."""

    name_no_html = name[:-5]  # remove ".html" from end

    dest_zip = os.path.join(
        output_dir, name_no_html + "_" + destination_id + ".html.zip"
    )

    print('Creating viewable archive "' + dest_zip + '"')

    logging.info("Zipping html at location: %s", os.path.abspath(os.curdir))
    command = ["zip", "-q", "-r", dest_zip, "index.html"]

    # find all directories called 'figures' and add them to the archive
    # for root, dirs, files in os.walk(path):
    #     for name in dirs:
    #         if name == "figures":
    #             figures_path = root.split("/")[-1] + "/figures"
    #             command.append(figures_path)
    #             print(f"including {figures_path}")

    # find all
    if include_ref_htmls:
        ref_htmls = glob.glob("*.html")
        for fl in ref_htmls:
            if "index.html" not in fl:
                command.append(fl)

    # log command as a string separated by spaces
    print(f"pwd = %s", Path.cwd())
    print(" ".join(command))

    result = sp.run(command, check=True)


def zip_feat_htmls(feat_dir, output_dir, destination_id):
    """Zip FEAT htmls at given path, include relative hyperlinks
    for all htmls (and figures?)

    Args:
        feat_dir:               target feat directory
        output_dir: (str)       where html.zips should be stored
        destination_id: (str)   suffix for html.zip files
    """

    # set working dir to reset at cleanup
    workdir = os.path.abspath(os.curdir)

    featbasefile = "report.html"

    # parse inputs
    if feat_dir is None or not Path(feat_dir).exists():
        raise logging.error("zip_feat_htmls error: path does not exist: %s", feat_dir)
    else:
        feat_dir = Path(feat_dir).absolute()

    if output_dir is None or not Path(output_dir).exists():
        raise logging.error("zip_feat_htmls error: path does not exist: %s", output_dir)
    else:
        output_dir = Path(output_dir).absolute()

    if os.path.exists(feat_dir):

        print("Found path: " + str(feat_dir))

        os.chdir(feat_dir)

        html_files = []
        # feat / gfeat files that should be zipped with other hyperlink files
        if any(featbasefile in x for x in os.listdir(feat_dir)):

            # first make a new writable copy of html in temp directory
            os.makedirs(os.path.join(output_dir, "tmp/"), exist_ok=True)
            os.system("cp " + os.path.join(feat_dir, featbasefile) + " " + os.path.join(output_dir, "tmp/"))

            # build html_files list
            html_files.append(os.path.join(output_dir, "tmp", featbasefile))

            # remove absolute paths from all html links
            ref_htmls = set_relative_hyperlinks(html_files[0])

            # repeat process for all referenced htmls
            for fl in ref_htmls:
                # check for references in each html file (only go one level for now, not full walker)
                itr_ref_htmls = set_relative_hyperlinks(fl)
                if os.path.exists(str(fl)):
                    os.system("cp " + str(fl) + " " + os.path.join(output_dir, "tmp/"))
                else:
                    logging.exception("Path not found: %s", str(fl))

                # copy all additional referenced htmls to zipping directory
                for itr_fl in itr_ref_htmls:
                    if os.path.exists(itr_fl):
                        os.system("cp " + itr_fl + " " + os.path.join(output_dir, "tmp/"))
                    else:
                        logging.exception("Path not found: %s", itr_fl)

            # use temp directory (containing feat report.html + reference htmls) for zip step
            os.chdir(os.path.join(output_dir, "tmp/"))

            # zip it!
            os.rename(featbasefile, "index.html")
            try:
                zip_it_zip_it_good(
                    output_dir, destination_id, featbasefile,
                    os.path.join(output_dir, "tmp/"),
                    include_ref_htmls=True
                )
            except:
                raise
            finally:
                os.rename("index.html", featbasefile)


        # clean-up
        if os.path.exists(os.path.join(output_dir, "tmp/")) and os.path.isdir(os.path.join(output_dir, "tmp/")):
            shutil.rmtree(os.path.join(output_dir, "tmp/"))
        os.chdir(workdir)


def zip_htmls(output_dir, destination_id, path, inputfile=None):
    """Zip all .html files at the given path so they can be displayed
    on the Flywheel platform.
    Each html file must be converted into an archive individually:
      rename each to be "index.html", then create a zip archive from it.
      Args:
          path(str)             location of html files to zip
          output_dir(str)       where html.zips should be stored
          destination_id(str)   suffix for html.zip files
          inputfile (str)       html file name if only one should be zipped
    """
    # set working dir to reset at cleanup
    workdir = os.path.abspath(os.curdir)
    # parse inputs
    if path is None or not Path(path).exists():
        raise logging.error("zip_htmls error: path does not exist: %s", path)
    else:
        path = Path(path).absolute()

    if output_dir is None or not Path(output_dir).exists():
        raise logging.error("zip_htmls error: path does not exist: %s", output_dir)
    else:
        output_dir = Path(output_dir).absolute()

    print("Creating viewable archives for all html files")

    if os.path.exists(path):

        print("Found path: " + str(path))

        os.chdir(path)
        html_files = []

        if not inputfile:
            html_files = glob.glob("*.html")
        else:
            html_files.append(inputfile)

        if len(html_files) > 0:

            # if there is an index.html, do it first and re-name it for safe
            # keeping
            save_name = ""
            if os.path.exists("index.html"):
                print("Found index.html")
                zip_it_zip_it_good(output_dir, destination_id, "index.html", path)

                now = datetime.datetime.now()
                save_name = now.strftime("%Y-%m-%d_%H-%M-%S") + "_index.html"
                os.rename("index.html", save_name)

                html_files.remove("index.html")  # don't do this one later

            for h_file in html_files:
                print("Found %s", h_file)
                os.rename(h_file, "index.html")
                try:
                    zip_it_zip_it_good(output_dir, destination_id, h_file, path)
                except:
                    raise
                finally:
                    os.rename("index.html", h_file)

            # restore if necessary
            if save_name != "":
                os.rename(save_name, "index.html")

        else:
            print("No *.html files at " + str(path))

    else:

        print("Path NOT found: " + str(path))

    # cleanup
    os.chdir(workdir)
