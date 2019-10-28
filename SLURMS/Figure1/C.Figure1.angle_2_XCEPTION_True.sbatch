#!/bin/bash
#SBATCH -p GTX980 # Partition to use
#SBATCH -n 1 # Number of cores
#SBATCH -N 1 # Ensure that all cores are on one machine
#SBATCH --gres=gpu:GTX980:4
#SBATCH --array=2
#SBATCH --mem=32000
#SBATCH -t 3-00:00
##SBATCH --mail-type=ALL
##SBATCH --mail-user=manish.mourya001@umb.edu
#SBATCH -o /home/manish.mourya001/Prof_Daniel/perception/SLURMS/Figure1/LOGS/%A_%a.out
#SBATCH -e /home/manish.mourya001/Prof_Daniel/perception/SLURMS/Figure1/LOGS/%A_%a.err
# Print this sub-job's task ID
echo "My SLURM_ARRAY_TASK_ID: " $SLURM_ARRAY_TASK_ID

##source new-modules.sh

##module load Anaconda/5.0.1-fasrc01

cd /home/manish.mourya001/Prof_Daniel/perception/EXP/

source activate CP

python run_regression.py C.Figure1.angle 2 XCEPTION True $SLURM_ARRAY_TASK_ID

# end
exit 0;
