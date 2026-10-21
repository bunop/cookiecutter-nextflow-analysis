#SBATCH --account=<account>             # account name
#SBATCH --partition=g100_usr_prod       # partition name (see https://docs.hpc.cineca.it/hpc/galileo.html#job-managing-and-slurm-partitions)
#SBATCH --qos=g100_qos_lprod            # quality of service: g100_qos_lprod if time > 24h, otherwise normal (see https://docs.hpc.cineca.it/hpc/galileo.html#job-managing-and-slurm-partitions)