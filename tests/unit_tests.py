# unit tests for functions...
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
from fmriprep import data_tree
from utils.utils import get_project_id, analysis_exists, zip_htmls

log = logging.getLogger(__name__)


data_tree('/home/mri/Documents/flywheel-apps/data_ingestion_tools','data_tree.txt')
