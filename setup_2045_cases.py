from datetime import datetime as dt
import pandas as pd
from pathlib import Path
import os


def transfer_2030_results():
    cwd = Path.cwd()
    policy_names = [f"s{x}" for x in range(1, 12)] + [f"p{x}" for x in range(1, 9)]
    folders_2030 = [
        folder
        for folder in (cwd / "2030/Complete").glob("*/")
        if os.path.isdir(folder) and folder.name[:2] in policy_names
    ]
    folders_2045 = [
        folder
        for folder in (cwd / "2045").glob("*/")
        if os.path.isdir(folder) and folder.name[:2] in policy_names
    ]
    # match the 2045 case to the 2030 case preceeding it
    policy_matches = {
    	"p1": "p1",
        "p2": "p2",
        "p3": "p1",
        "p4": "p4",
        "p5": "p5",
        "p6": "p6",
        "p7": "p7",
        "p8": "p8",
        "s1": "s1",
        "s2": "s2",
        "s3": "s3",
        "s4": "s4",
        "s5": "s5",
        "s6": "s6",
        "s7": "s7",
        "s8": "s8",
        "s9": "s9",
        "s10": "s10",
        "s11": "s11",
        "s12": "s12",
    }

    # folder_pairs = {f: f.replace("2030", "2045") for f in folders}

    for p_2045, p_2030 in policy_matches.items():
        try:
            f_2030 = [f / "Results" for f in folders_2030 if f.name[:2] == p_2030][0]
        except IndexError:
            print(f"No folder for case {p_2030}")
            f_2030 = None

        try:
            f_2045 = [f / "Inputs" for f in folders_2045 if f.name[:2] == p_2045][0]
        except IndexError:
            print(f"No folder for case {p_2045}")

        update_text_path = f_2045.parent / "inputs_updated.txt"
        if f_2030 is not None:
            if update_text_path.exists():
                print(f"2045 policy {p_2045} inputs have already been modified.")

            else:
                print(f"Reading capacity results from {p_2030}")
                capacity_2030 = pd.read_csv(f_2030 / "Capacity.csv")
                capacity_2030 = capacity_2030.loc[
                    capacity_2030["Resource"] != "Total", :
                ]

                gen_data_2045 = pd.read_csv(f_2045 / "Generators_data.csv")
                gen_data_2045.loc[
                    gen_data_2045["Resource"] != "ev_load_shifting", "Existing_Cap_MW"
                ] = (
                    capacity_2030.loc[
                        capacity_2030["Resource"] != "ev_load_shifting", "EndCap"
                    ]
                    .round(2)
                    .values
                )
                gen_data_2045.loc[:, "Existing_Cap_MWh"] = (
                    capacity_2030["EndEnergyCap"].round(2).values
                )

                gen_data_2045.to_csv(f_2045 / "Generators_data.csv", index=False)

                network_2030 = pd.read_csv(f_2030 / f"Network_expansion.csv")
                network_data_2045 = pd.read_csv(f_2045 / "Network.csv")

                network_data_2045.loc[:, "Line_Max_Flow_MW"] += (
                    network_2030["New_Trans_Capacity"].round(2).values
                )

                network_data_2045.to_csv(f_2045 / "Network.csv", index=False)

                now = dt.now().strftime("%Y-%m-%d %H.%M.%S")
                update_text_path.write_text(
                    f"Inputs modifed with previous period results (case {p_2030}) on {now}"
                )

                print(f"Updated inputs written for 2045 case {p_2045}")
        else:
            print(f"No results folder for 2030 policy {p_2030}")


if __name__ == "__main__":
    transfer_2030_results()
