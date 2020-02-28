"Calculate region-specific costs from imports/exports/RPS/CES"

import os
from pathlib import Path

import pandas as pd
import yaml


def find_results_folders(year):
    cwd = Path.cwd()

    results_folders = list((cwd / f"{year}").rglob("Results"))
    results_folders.sort()

    return results_folders


def clean_case_name(name):
    clean_name = " ".join(name.split("_")[2:]).replace("with", "w/").strip()

    return clean_name


def find_years():

    years = [
        int(f.name)
        for f in os.scandir(Path.cwd())
        if f.is_dir() and "__" not in f.name and "." not in f.name
    ]

    return years


def find_region_lines():
    "Returns a dictionary of zone number: list of "
    network_file_path = list(Path.cwd().rglob("Network.csv"))[0]

    network_df = pd.read_csv(network_file_path)
    network_df = network_df.set_index("Network_lines")

    # Zones should be of form "z<x>" where x is an integer
    zones = network_df["Network_zones"].dropna().to_list()
    if "Region description" in network_df.columns:
        zone_names = network_df["Region description"].dropna().to_list()
    else:
        zone_names = zones
    zone_lines = {}
    for zone, name in zip(zones, zone_names):
        zone_lines[name] = network_df.loc[network_df[zone] != 0, :].index.to_list()

    return zone_lines


def calc_import_export_costs(year, zone, lines):
    zone_num = int(zone[1:])
    results_folders = find_results_folders(year)
    input_folders = [folder.parent / "Inputs" for folder in results_folders]
    # col_order = [clean_case_name(folder.parent.stem) for folder in results_folders]

    imports_dict = {}
    exports_dict = {}
    for i_folder, r_folder in zip(input_folders, results_folders):
        case_name = clean_case_name(i_folder.parent.stem)
        flow = pd.read_csv(r_folder / "flow.csv", index_col=0)
        prices = pd.read_csv(r_folder / "prices.csv", index_col=0)
        network = pd.read_csv(i_folder / "Network.csv")

        network_direction = network.set_index("Network_lines")[zone]

        imports = 0
        exports = 0

        # print(case_name)
        for line in lines:
            line_imports = flow.loc[
                network_direction[line] * flow[f"{line}"] < 0, f"{line}"
            ]
            line_exports = flow.loc[
                network_direction[line] * flow[f"{line}"] > 0, f"{line}"
            ]

            line_import_costs = (
                -1
                * network_direction[line]
                * (line_imports * prices[f"{zone_num}"]).dropna().sum()
            )
            imports += line_import_costs

            line_export_revenues = (
                -1
                * network_direction[line]
                * (line_exports * prices[f"{zone_num}"]).dropna().sum()
            )
            exports += line_export_revenues

        imports_dict[case_name] = imports
        exports_dict[case_name] = exports

    import_export_df = pd.DataFrame(
        [imports_dict, exports_dict], index=["Import Costs", "Export Revenues"]
    ).T
    import_export_df["Net Trade Costs"] = import_export_df.sum(axis=1)
    import_export_df = import_export_df.astype(int)
    # import_export_df["Zone"] = year

    return import_export_df


def calc_rps_ces_costs(year, zone):
    zone_num = int(zone[1:])
    results_folders = find_results_folders(year)
    input_folders = [folder.parent / "Inputs" for folder in results_folders]
    # col_order = [clean_case_name(folder.parent.stem) for folder in results_folders]

    rps_dict = {}
    ces_dict = {}
    for i_folder, r_folder in zip(input_folders, results_folders):
        case_name = clean_case_name(i_folder.parent.stem)
        # print(case_name, year)

        genx_settings_path = i_folder.parent / "GenX_settings.yml"
        with open(genx_settings_path, "r") as f:
            settings = yaml.safe_load(f)
        rps_adjustment = settings["RPS_Adjustment"]
        ces_adjustment = settings["CES_Adjustment"]

        rps_ces_prices = pd.read_csv(r_folder / "RPS_CES.csv", index_col=0)
        rps_price = rps_ces_prices.loc[zone_num, "RPS_Price"]
        ces_price = rps_ces_prices.loc[zone_num, "CES_Price"]

        generators = pd.read_csv(i_folder / "Generators_data.csv")
        resource_rps_value = generators.loc[generators["zone"] == zone_num, "RPS"]
        resource_ces_value = generators.loc[generators["zone"] == zone_num, "CES"]

        energy = pd.read_csv(r_folder / "Power.csv", index_col=0)

        # Calculate the weighted generation for every resources
        weighted_gen = energy.loc["Sum", :].reset_index(drop=True)

        # Credits from in-region generation by qualifying resources
        region_rps_credits = (weighted_gen * resource_rps_value).sum()
        region_ces_credits = (weighted_gen * resource_ces_value).sum()

        network = pd.read_csv(i_folder / "Network.csv", index_col=1)

        # Calculate how many credits are needed in a region
        qualifying_resources = generators.loc[
            (generators["zone"] == zone_num)
            & (generators["STOR"] == 0)
            & (generators["DR"] == 0)
            & (generators["HEAT"] == 0),
            :,
        ].index
        qualifying_energy = weighted_gen.loc[qualifying_resources].sum()
        region_rps_requirement = (
            network.loc[zone, "RPS"] * qualifying_energy
        ) - rps_adjustment
        region_ces_requirement = (
            network.loc[zone, "CES"] * qualifying_energy
        ) - ces_adjustment

        rps_credit_difference = region_rps_requirement - region_rps_credits
        ces_credit_difference = region_ces_requirement - region_ces_credits

        rps_cost = rps_credit_difference * rps_price
        ces_cost = ces_credit_difference * ces_price

        rps_dict[case_name] = rps_cost
        ces_dict[case_name] = ces_cost

    rps_ces_df = (
        pd.DataFrame([rps_dict, ces_dict], index=["RPS Costs", "CES Costs"])
        .T.fillna(0)
        .astype(int)
    )
    # rps_ces_df["Zone"] = zone

    return rps_ces_df


def calc_all_costs():
    years = find_years()
    zone_dict = find_region_lines()
    results_list = []
    for year in years:
        for zone, zone_lines in zone_dict.item():
            import_export_df = calc_import_export_costs(year, zone, zone_lines)
            rps_ces_df = calc_rps_ces_costs(year, zone)

            combined_df = pd.concat([import_export_df, rps_ces_df], axis=1)
            combined_df["Total Extra Costs"] = combined_df[
                ["Net Trade Costs", "RPS Costs", "CES Costs"]
            ].sum(axis=1)
            combined_df["Year"] = year
            combined_df["Zone"] = zone

            results_list.append(combined_df)

    final_costs = pd.concat(results_list)
    final_costs.index.name = "Case"
    final_costs = final_costs.reset_index().set_index(["Year", "Case"])

    return final_costs


def main():
    final_costs = calc_all_costs()

    final_costs.to_csv("Zone specific costs.csv")


if __name__ == "__main__":
    main()
