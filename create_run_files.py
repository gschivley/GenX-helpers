"Create copies of Run.jl and Run.sh in each case folder"

import shutil
from pathlib import Path
import textwrap


def find_all_sub_folders():
    cwd = Path.cwd()

    subitems = cwd.rglob("GenX_settings.yml")

    subfolders = [f.parent for f in subitems if f.parent != cwd]

    return subfolders


def write_shell_script(dest_folder):

    # I'm just using the case ID here. You could use any part of the folder name
    # instead. Folder names are <case_id>_<year>_<case_description>
    short_name = dest_folder.stem.split("_")[0]
    # For example, the case description would be:
    # short_name = "_".join(dest_folder.stem.split("_")[2:])

    shell_text = textwrap.dedent(
        f"""\
        #!/bin/bash

        #SBATCH --job-name="{short_name}"       # Create a short name for your job
        #SBATCH --time=12:00:00       # Set total runtime limit (HH:MM:SS). Note: Queue time limits: test=1 hr; short=24 hrs; medium=72 hrs; long=144 hours

        #SBATCH --nodes=1             # Number of nodes
        #SBATCH --ntasks=1            # Total number of tasks across all nodes
        #SBATCH --cpus-per-task=4     # CPUs per task (8-16 recommended)
        #SBATCH --mem-per-cpu=4000      # memory per cpu-core

        #SBATCH --mail-type=begin       # notifications for job started
        #SBATCH --mail-type=fail      # notifications for job failed
        #SBATCH --mail-type=end       # notifications for job completed
        #SBATCH --mail-user=jdj2@princeton.edu  # send-to address

        #SBATCH --output="/home/jdj2/Arizona/{dest_folder.stem}/juliaTest.%j.%N.out"  # Path to write output
        #SBATCH --error="/home/jdj2/Arizona/{dest_folder.stem}/juliaTest.%j.%N.err"   # Path to error logs

        module add julia/1.2.0
        module add CPLEX

        julia /home/jdj2/Arizona/{dest_folder.stem}/Run.jl


        date
    """
    # """\
    # #!/bin/bash
    # julia Run.jl
    # """
    )
    shell_file = dest_folder / "Run.sh"
    shell_file.write_text(shell_text)


def copy_run_files():
    cwd = Path.cwd()
    subfolders = find_all_sub_folders()

    source_file = cwd / "Run.jl"

    for folder in subfolders:
        dest_file = folder / "Run.jl"
        shutil.copyfile(source_file, dest_file)

        write_shell_script(folder)


if __name__ == "__main__":
    copy_run_files()
