# GenX-helpers

Misc helper files for working with GenX inputs/results

All files are (currently) written in Python. Installing the `powergenome` [conda environment from PowerGenome](https://github.com/gschivley/PowerGenome#installation) will cover most of the requirements. Additional dependencies include:

- [altair](https://altair-viz.github.io/index.html) for figures (`conda install -c conda-forge altair`)
- [typer](https://typer.tiangolo.com/) for command line options in `compile_results.py` (`pip install typer`)

## File descriptions

### create_run_files

Copy a `Run.jl` file into all case subfolders and write a `Run.sh` file.

### setup_2045_cases

Transfer results (capacity changes and transmission expansion) from 2030 runs forward into the 2045 inputs. 2030 cases need to be in a "Complete" folder. The script adds a text file `inputs_updated` to 2045 cases once they are modified and won't modify them again if this text file is detected.

There is a `setup_2045.jl` file that uses PyCall to call the main Python function.

### zone_trade_attribute_cost

Calculate the import/export/RPS/CES costs for each zone. This file should be generalized to work on any set of GenX results. Results are exported as a csv if the script is run from command line.

### compile_results

Create results figures and an excel file. This file is mostly generalized but uses the `calc_all_costs` function from `zone_trade_attribute_cost.py` and assumes that it only has results for the WECC_AZ region.

The script will create both figures and the excel file by default. The command line flags `--no-figures` and `--no-excel` can be used to not create one of the two.

At the top of the file are dictionaries to map resources names from results to names used in the figures/Excel. These matches are done using `.str.contains()` in Pandas so they can be partial versions of the resource name. The lists `POLICY_ORDER` and `SENSITIVITY_ORDER` are names of cases (derived from folder names) that get used in different figures. This can be generalized into a dictionary of lists rather than forcing cases into the two categories. Keys from the list would be used in file names.

Figures include:

- Combined energy cost ($/MWh), CO2 emissions, installed capacity, and energy shares in each planning period.
- Changes in capacity (additions and retirements by resource type) across the planning periods.
- Spur line and inter-regional transmission expansion (both cost and capacity) for both periods.
- Transmission capacity for each line across existing, 2030, and 2045.

Excel files are created for total results and by region. Each file has the following sheets for every planning period with results for all cases:

- Capacity (start, final, and changes)
- Energy
- Emissions
- Network expansion (capacity and cost)
- Spur line (capacity-miles and cost)
- Costs (including spur-line investment from previous planning period)
- Demand
- Energy cost ($/MWh)
