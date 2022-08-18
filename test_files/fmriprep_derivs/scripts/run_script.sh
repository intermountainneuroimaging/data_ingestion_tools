#!/bin/bash
#
#SBATCH --job-name=fmriprep
#SBATCH --time=24:00:00
#SBATCH --output=<path>
#SBATCH --error=<path>
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G


# ---------------------------------------------------
# Example sbatch: launch fmriprep job array
# ---------------------------------------------------
# Description: Use this example script to build fmriprep
#              singularity job for BIDS inputs. Job array
#                          allows user to control how many jobs are 
#              launched together. 
#              !! Test job submission first with a single job !!

module purge
module load singularity/3.6.4
#
image=/pl/active/ics/containers/fmriprep/fmriprep-v.21.0.0.sif
#
studydir=<path>
#
# !! Freesurfer license location should be updated!! ##
fslicense=license.txt
#
outdir=$studydir/Analysis/fmri
bidsdir=$studydir/BIDS
mkdir -p $outdir

# get list of subjects for analysis
subjfile=$outdir/analysislist.txt
ls -1 $studydir/BIDS | grep "sub-" | cut -d'-' -f2 > $subjfile

bidsdir=$studydir/BIDS

logdir=$outdir/logs
mkdir -p $logdir

# Set up job array index - calls subject number from list of inputs
NUM=$SLURM_ARRAY_TASK_ID
SUBJECT=$(sed -n "$NUM"p $subjfile)
echo "Running: $SUBJECT"

# setup working directory (needed for parallel execution) and logs location
workdir=/rc_scratch/$USER/scratch/sub-${SUBJECT}
mkdir -p $workdir
olog=$logdir/fmriprep_sub-${SUBJECT}.o$SLURM_ARRAY_JOB_ID
elog=$logdir/fmriprep_sub-${SUBJECT}.e$SLURM_ARRAY_JOB_ID

export SINGULARITY_TMPDIR=/projects/$USER
export SINGULARITY_CACHEDIR=/projects/$USER

unset PYTHONPATH

# if output does not yet exist, run...
if [ ! -f $outdir/sub-${SUBJECT}.html ]; then
        singularity run --cleanenv -B $bidsdir:/data -B $outdir:/out -B $workdir:/work $image /data /out participant --participant_label $SUBJECT -w /work --ignore slicetiming --output-space {func,MNI152NLin2009cAsym:res-2} --use-aroma --aroma-melodic-dimensionality -100 --fs-license-file $fslicense --mem 62000 --no-submm-recon --write-graph --notrack --omp-nthreads 1 --skull-strip-fixed-seed   1>$olog 2>$elog
fi

# remove scratch directory after complete
# rm -R $workdir

## fmriprep options:
#     --omp-nthreads 1 <and> --skull-strip-fixed-seed --> used for reliable execution, remove stocasticity 
#     --notrack prevents fmriprep from senting metrics on your dataset to their server
#     -- write-graph prints a workflow diagram