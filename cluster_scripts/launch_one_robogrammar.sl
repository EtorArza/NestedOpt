#!/bin/bash
###   s b a t c h --array=1-$runs:1 $SL_FILE_NAME
#SBATCH --ntasks=1 # number of tasks
#SBATCH --ntasks-per-node=1 #number of tasks per node
#SBATCH --mem=240G
#SBATCH --cpus-per-task=32 # number of CPUs
#SBATCH --output=/workspace/scratch/jobs/earza/slurm_logs/slurm_%A_%a_%x_out.txt
#SBATCH --error=/workspace/scratch/jobs/earza/slurm_logs/slurm_%A_%a_%x_err.txt
#SBATCH --time=5-00:00:00 #Walltime
#SBATCH -p large
#SBATCH --exclude=n[001-004]

echo "--"


module load Python/3.9.5-GCCcore-10.3.0
module load CMake/3.20.1-GCCcore-10.3.0
module load libGLU/9.0.1-GCCcore-10.3.0
module load X11/20210518-GCCcore-10.3.0
module load GLib/2.68.2-GCCcore-10.3.0
module load libglvnd/1.3.3-GCCcore-10.3.0
module load Mesa/21.1.1-GCCcore-10.3.0
module load xorg-macros/1.19.3-GCCcore-10.3.0
module load Xvfb/1.20.9-GCCcore-10.2.0 2>/dev/null
source venv/bin/activate


echo "Loaded modules."
echo -n "Start src/robogrammar_experiment.py --local_launch $SLURM_ARRAY_TASK_ID | "
date
python src/robogrammar_experiment.py --local_launch $SLURM_ARRAY_TASK_ID
echo -n "Done src/robogrammar_experiment.py --local_launch $SLURM_ARRAY_TASK_ID | "
date

n_visualizations=45
if [ "$SLURM_ARRAY_TASK_ID" -gt "$n_visualizations" ]; then
echo -n "Generating visualization:"
date
xvfb-run -a python src/robogrammar_experiment.py --visualize $SLURM_ARRAY_TASK_ID
echo -n "Done generating visualization:"
date
fi
echo "--"


