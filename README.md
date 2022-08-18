# Flyhweel.io Analysis Data Ingestion Toolbox

The following toolbox was developed to leverage Flywheel.io's Python SDK to import retropectively generated neuroimaging analyses. Specifically, we are in development to create a tool for the following preprocessing and modeling tools:
- fmriprep
- FSL FEAT (1st level models, 2nd level models)
- custom preprocessing (BIDS derivative naming)
- and more!

This toolbox uses poetry for dependency mangagement, and Python 3.9. Feel free to take your own steps to install Python and Poetry, but if you want to follow along here, we can get you where you need to go!

If you do not have Python 3.9 installed, we suggest installing Python via [Anaconda](https://www.anaconda.com/). Follow the instructions on Anaconda's website based on your operating system.

Once you have installed anaconda, and working in a conda enviornment. We next need to install [poetry](https://python-poetry.org/docs/):
```
pip install poetry
```

Once poetry is installed, choose a location to pull the code base...
```
cd ~/Documents/
git clone https://github.com/intermountainneuroimaging/data_ingestion_tools.git
```

Next you will want to start from within the repository to use the tools
```
cd data_ingestion_tools
```

Check out how to use one of our tools as follows:

```
python fmriprep_upload.py --help
```

Remember this site is under ***active*** development so before using any tools, make sure to pull the latest version.

```
git pull
```

## Getting Started: FmriPrep Uploads

To upload an fmriprep retrospective analysis you will start with example code such as the following:
```
python fmriprep_upload.py <path-to-fmriprep-data> <group> <project> --subject LABEL --session LABEL
```

Here, we will infer the fmriprep derivative data you want to upload based on the path to your fmriprep directory and the subject and session information provided. Once sucessfully uploaded, you will see a new analysis in the identified subject and session within Flywheel called "bids-fmriprep."

A few important points to keep in mind, we do require specific file structure for sucessful upload. An example format is provided in this repository, and is detailed below.
```
Source Data Path - should be fmriprep parent directory

fmriprep
  |--sub-001
     |--ses-01
        |--anat
          |--files...
        |--func
          |--files...
  |--sub-002
  ...
  |--logs  <<------- ADD Logs directory with all compute logs (this 
                               can be overwritten with --log-path flag)
  |--scripts <<----- ADD scripts directory with all computer code used 
                               to generate results (this can be overwritten
                               with --scripts-path flag)
  |--analysis_configuration.txt   <<----- This file most exist here, 
                                          containing the configuration 
                                          settings used in the pipeline
  |--analysis_information.txt     <<----- This file must exist here,
                                          containing the information about
                                          the executed pipeline or software
```

See examples of this directory structure in: `test_files/fmriprep_derivs`