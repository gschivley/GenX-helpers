"Quickly compile results across cases for comparison"

import os
from pathlib import Path
import pandas as pd
import typer

import altair as alt

from powergenome.nrelatb import investment_cost_calculator
from zone_trade_attribute_costs import calc_all_costs

app = typer.Typer()

RESOURCE_MAP = {
    "coal": "Coal",
    "ccs": "CCS",
    "turbine": "NGCT",
    "combined_cycle": "NGCC",
    "ccavg": "NGCC",
    "ctavg": "NGCT",
    "landbasedwind": "Onshore Wind",
    "onshore_wind": "Onshore Wind",
    "offshorewind": "Offshore Wind",
    "utilitypv": "Solar",
    "solar": "Solar",
    "conventional_hydro": "Hydro",
    "battery": "Battery",
    "nuclear": "Nuclear",
    "biomass": "Other Renewables",
    "geothermal": "Other Renewables",
    "small_hydroelectric": "Other Renewables",
    "pumped_hydro": "Pumped Hydro",
}
ZONE_MAP = {
    1: "CA_N",
    2: "CA_S",
    3: "WECC_AZ",
    4: "WECC_CO",
    5: "WECC_NM",
    6: "WECC_NW",
    7: "WECC_SNV",
}
POLICY_ORDER = [
    "No Policy",
    "Emissions Cap w/ RPS",
    "WRA CES w/ RPS",
    "Tech CES w/ RPS",
    "RPS only",
    "Emissions Cap",
    "WRA CES",
    "Tech CES",
]
SENSITIVITY_ORDER = [
    "No Policy",
    "WRA CES",
    "WRA CES w/ RPS",
    "Coal Phaseout",
    "Coal Phaseout No New Gas",
    "No New Gas",
    "Slower AZ load growth",
    "Half WECC load growth",
    "Limits transmission",
    "High EV penetration",
    "Low cost nuclear",
    "Low gas prices",
    "Low cost CCS",
    "High cost CCS",
    "Low cost renewables",
]
RESOURCE_ORDER = [
    "Coal",
    "NGCC",
    "NGCT",
    "Other Renewables",
    "Nuclear",
    "CCS",
    "Hydro",
    "Pumped Hydro",
    "Battery",
    "Solar",
    "Onshore Wind",
    "Offshore Wind",
][::-1]
RESOURCE_COLOR_SCALE = alt.Scale(
    domain=RESOURCE_ORDER,
    range=[
        "#8c564b",  # coal
        "#bcbd22",  # NGCC
        "#dbdb8d",  # NGCT
        "#9467bd",  # other renewables
        "#7f7f7f",  # Nuclear
        "#c7c7c7",  # CCS
        "#1f77b4",  # hydro
        "#aec7e8",  # pumped hydro
        "#c5b0d5",  # battery
        "#d62728",  # solar
        "#17becf",  # onshore wind
        "#9edae5",  # offshore wind
    ][::-1],
)
RESOURCE_COLORS = alt.Color("Resource Name", scale=RESOURCE_COLOR_SCALE)
RESOURCE_ORDER_DICT = {
    resource: idx for idx, resource in enumerate(RESOURCE_ORDER[::-1])
}


def find_years():
    years = [
        int(f.name)
        for f in os.scandir(Path.cwd())
        if f.is_dir() and "__" not in f.name and "." not in f.name
    ]
    years = sorted(years)

    return years


def make_data_tidy(df, value_name, id_vars=["Resource Name"]):
    tidy = df.reset_index().melt(
        id_vars=id_vars, var_name="Case", value_name=value_name
    )
    return tidy


def clean_case_name(name):
    clean_name = " ".join(name.split("_")[2:]).replace("with", "w/").strip()

    return clean_name


def clean_tx_line_name(line_series):
    clean_names = line_series.str.replace("_to_", " to ")

    return clean_names


def find_results_folders(year):
    cwd = Path.cwd()

    results_folders = list((cwd / f"{year}").rglob("Results"))
    results_folders.sort()

    return results_folders


def map_resource_name(df):
    df["Resource Name"] = None
    for key, value in RESOURCE_MAP.items():
        df.loc[df["Resource"].str.contains(key), "Resource Name"] = value

    return df


def get_resource_capacity(year):
    results_folders = find_results_folders(year)
    col_order = [clean_case_name(folder.parent.stem) for folder in results_folders]

    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        capacity_df = pd.read_csv(folder / "capacity.csv")
        capacity_df["Region"] = capacity_df["Zone"].map(ZONE_MAP)
        capacity_df = capacity_df.drop(columns=["Zone"])
        capacity_df["Case"] = case_name
        capacity_df["R_ID"] = capacity_df.index + 1
        df_list.append(capacity_df)

    capacity_comparison = pd.concat(df_list, sort=False)
    capacity_comparison = capacity_comparison.rename(
        columns={
            "EndCap": "Final Capacity",
            "StartCap": "Start Capacity",
            "RetCap": "Retired Capacity",
            "NewCap": "New Capacity",
            "EndEnergyCap": "Final Energy Capacity",
            "EndChargeCap": "Final Charge Capacity",
            "StartEnergyCap": "Start Energy Capacity",
            "RetEnergyCap": "Retired Energy Capacity",
            "NewEnergyCap": "New Energy Capacity",
            "StartChargeCap": "Start Charge Capacity",
            "RetChargeCap": "Retired Charge Capacity",
            "NewChargeCap": "New Charge Capacity",
        }
    )
    # return capacity_comparison
    capacity_comparison = (
        capacity_comparison.pivot_table(
            columns="Case", index=["Region", "Resource", "R_ID"]
        )
        .stack(0)
        .reset_index()
        .rename(columns={"level_3": "Category"})
        .set_index(["Region", "Category", "Resource", "R_ID"])
    )
    for col in capacity_comparison.columns:
        if "Retired" in col:
            capacity_comparison.loc[:, col] *= -1

    return capacity_comparison[col_order]


def compare_capacity(year):
    results_folders = find_results_folders(year)
    col_order = [clean_case_name(folder.parent.stem) for folder in results_folders]

    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        capacity_df = pd.read_csv(folder / "capacity.csv")
        capacity_df = map_resource_name(capacity_df)
        capacity_df["Region"] = capacity_df["Zone"].map(ZONE_MAP)
        grouped_capacity = capacity_df.groupby(["Region", "Resource Name"]).sum()
        grouped_capacity["Case"] = case_name
        grouped_capacity = grouped_capacity.drop(columns=["Zone"])

        df_list.append(grouped_capacity)

    capacity_comparison = pd.concat(df_list, sort=False)
    capacity_comparison = capacity_comparison.rename(
        columns={
            "EndCap": "Final Capacity",
            "StartCap": "Start Capacity",
            "RetCap": "Retired Capacity",
            "NewCap": "New Capacity",
            "EndEnergyCap": "Final Energy Capacity",
            "EndChargeCap": "Final Charge Capacity",
            "StartEnergyCap": "Start Energy Capacity",
            "RetEnergyCap": "Retired Energy Capacity",
            "NewEnergyCap": "New Energy Capacity",
            "StartChargeCap": "Start Charge Capacity",
            "RetChargeCap": "Retired Charge Capacity",
            "NewChargeCap": "New Charge Capacity",
        }
    )

    # This is a mess and I'm not sure it gives the best format output.
    capacity_comparison = (
        capacity_comparison.pivot_table(
            columns="Case", index=["Region", "Resource Name"]
        )
        .stack(0)
        .reset_index()
        .rename(columns={"level_2": "Category"})
        .set_index(["Region", "Category", "Resource Name"])
    )
    for col in capacity_comparison.columns:
        if "Retired" in col:
            capacity_comparison.loc[:, col] *= -1
    # cols = list(capacity_comparison.columns)
    # cols.sort()

    return capacity_comparison[col_order].round(1)


def load_energy_case(folder):
    case_name = clean_case_name(folder.parent.stem)
    energy_df = pd.read_csv(folder / "power.csv", header=None, index_col=0)
    energy_df = energy_df.T
    energy_df = map_resource_name(energy_df)
    energy_df["Zone"] = energy_df["Zone"].astype(int)
    energy_df["Sum"] = energy_df["Sum"].astype(float)
    energy_df["Region"] = energy_df["Zone"].map(ZONE_MAP)
    grouped_energy = energy_df.groupby(["Region", "Resource Name"]).sum()
    grouped_energy = grouped_energy.rename(columns={"Sum": case_name})

    return grouped_energy


def compare_energy(year):
    results_folders = find_results_folders(year)
    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        energy_df = pd.read_csv(folder / "power.csv", header=None, index_col=0)
        energy_df = energy_df.T
        energy_df = map_resource_name(energy_df)
        energy_df["Zone"] = energy_df["Zone"].astype(int)
        energy_df["Sum"] = energy_df["Sum"].astype(float)
        energy_df["Region"] = energy_df["Zone"].map(ZONE_MAP)
        grouped_energy = energy_df.groupby(["Region", "Resource Name"]).sum()
        grouped_energy = grouped_energy.rename(columns={"Sum": case_name})

        df_list.append(grouped_energy[[case_name]])

    energy_comparison = pd.concat(df_list, axis=1)
    cols = list(energy_comparison.columns)
    # cols.sort()

    return energy_comparison[cols].round(0)


def compare_emissions(year):
    results_folders = find_results_folders(year)
    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        emissions_df = pd.read_csv(folder / "emissions.csv", header=None, index_col=0)

        # Drop the last column (Total)
        emissions_df = emissions_df.iloc[:, :-1]
        emissions_df = emissions_df.T
        # emissions_df = map_resource_name(emissions_df)
        emissions_df["Zone"] = emissions_df["Zone"].astype(int)
        emissions_df["Sum"] = emissions_df["Sum"].astype(float)
        emissions_df["Region"] = emissions_df["Zone"].map(ZONE_MAP)
        grouped_emissions = emissions_df.groupby(["Region"]).sum()
        grouped_emissions = grouped_emissions.rename(columns={"Sum": case_name})

        df_list.append(grouped_emissions[[case_name]])

    emissions_comparison = pd.concat(df_list, axis=1)
    cols = list(emissions_comparison.columns)
    cols.sort()

    return emissions_comparison[cols].round(0)


def get_total_hours(year):
    results_folders = find_results_folders(year)

    load_data = pd.read_csv(
        list(results_folders)[0].parent / "Inputs" / "Load_data.csv"
    )
    total_hours = load_data["Sub_Weights"].sum()

    return total_hours


def compare_costs(year):
    results_folders = find_results_folders(year)
    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        costs_df = pd.read_csv(
            folder / "costs.csv", header=None, index_col=0, na_values=["-"]
        )

        costs_df = costs_df.loc[:, 2:].T
        costs_df["Zone"] = costs_df["Costs"].str.replace("Zone", "").astype(int)
        costs_df["Region"] = costs_df["Zone"].map(ZONE_MAP)
        costs_df["Case"] = case_name
        costs_df = costs_df.set_index(["Case", "Region"])
        costs_df = costs_df.drop(columns=["Zone", "Costs"])
        # costs_df = costs_df.T
        df_list.append(costs_df)

    cost_comparison = pd.concat(df_list, axis=0)
    cost_comparison = cost_comparison.astype(float)
    cost_comparison = cost_comparison.round(2)

    return cost_comparison


def compare_rps_ces_prices(year):
    results_folders = find_results_folders(year)
    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        rps_ces_df = pd.read_csv(folder / "RPS_CES.csv")
        rps_ces_df["Region"] = rps_ces_df["Zone"].map(ZONE_MAP)
        rps_ces_df["Case"] = case_name
        rps_ces_df = rps_ces_df.set_index(["case", "Region"])
        df_list.append(rps_ces_df)

    rps_ces_comparison = pd.concat(df_list)
    rps_ces_comparison = rps_ces_comparison.round(2)
    rps_ces_comparison = rps_ces_comparison.drop(columns="Zone")

    return rps_ces_comparison


def compare_tx_build(year):
    results_folders = find_results_folders(year)
    network_input = pd.read_csv(results_folders[0].parent / "Inputs" / "Network.csv")
    network_input = network_input.set_index("Network_lines")
    network_line_map = network_input["Transmission Path Name"]
    df_list = []
    for folder in results_folders:
        case_name = clean_case_name(folder.parent.stem)
        tx_df = pd.read_csv(folder / "network_expansion.csv")
        tx_df["Path Name"] = tx_df["Line"].map(network_line_map)
        tx_df["Path Name"] = tx_df["Path Name"].str.replace("_to_", " to ")
        tx_df["Case"] = case_name
        df_list.append(tx_df)

    tx_comparison = pd.concat(df_list)
    tx_comparison = tx_comparison.drop(columns=["Line"])
    tx_comparison = tx_comparison.set_index(["Case", "Path Name"])

    return tx_comparison.round(1)


def compare_spur_line_build(year):
    results_folders = find_results_folders(year)
    gen_input = pd.read_csv(
        results_folders[0].parent / "Inputs" / "Generators_data.csv"
    )
    gen_input = gen_input.set_index("R_ID")
    spur_line_miles_map = gen_input["spur_line_miles"]
    spur_line_capex_map = gen_input["spur_line_capex"]

    raw_cap = get_resource_capacity(year)
    new_cap = make_data_tidy(
        raw_cap,
        value_name="Capacity (MW)",
        id_vars=["Region", "Category", "R_ID", "Resource"],
    ).query("Category=='New Capacity'")

    new_cap = map_resource_name(new_cap)

    new_cap["resource_spur_miles"] = new_cap["R_ID"].map(spur_line_miles_map)
    new_cap["resource_spur_capex"] = new_cap["R_ID"].map(spur_line_capex_map)
    new_cap = new_cap.drop(columns=["R_ID"])

    new_cap["Spur Line MW-Miles"] = (
        new_cap["Capacity (MW)"] * new_cap["resource_spur_miles"]
    )
    new_cap["Spur Line Capex"] = (
        new_cap["Capacity (MW)"] * new_cap["resource_spur_capex"]
    )
    new_cap["Spur Line Inv Cost"] = investment_cost_calculator(
        new_cap["Spur Line Capex"], wacc=0.069, cap_rec_years=60
    )

    return new_cap


def compare_demand(year):
    results_folders = find_results_folders(year)
    input_folders = [folder.parent / "Inputs" for folder in results_folders]
    # load_dict = {}
    load_list = []
    for i_folder, r_folder in zip(input_folders, results_folders):
        case_name = clean_case_name(i_folder.parent.stem)
        load = pd.read_csv(i_folder / "Load_data.csv")
        time_weight = pd.read_csv(r_folder / "time_weights.csv")
        total_load = (
            load.loc[:, "Load_MW_z1":].mul(time_weight["Weight"], axis=0)
        ).sum()
        total_load.name = "Total Demand"
        total_load.index.name = "Zone"
        total_load = total_load.reset_index()
        total_load["Region"] = (
            total_load["Zone"].str.replace("Load_MW_z", "").astype(int).map(ZONE_MAP)
        )
        # load_dict[case_name] = total_load
        total_load["Case"] = case_name
        load_list.append(total_load)

    load_comparison = pd.concat(load_list)
    load_comparison = load_comparison.drop(columns=["Zone"])
    load_comparison = load_comparison.set_index(["Case", "Region"])

    # load_comparison = pd.Series(load_dict, name="Total Demand")

    return load_comparison


def add_coal_retirements(capacity_df, base_case, modify_case_list):
    idx = pd.IndexSlice
    coal_retirements = capacity_df.loc[idx[:, "Start Capacity", "Coal"], base_case]

    for case in modify_case_list:
        capacity_df.loc[
            idx[:, "Retired Capacity", "Coal"], case
        ] = coal_retirements.values
        capacity_df.loc[
            idx[:, "Start Capacity", "Coal"], case
        ] = coal_retirements.values

    return capacity_df


# def add_start


def build_results(year, prev_spur_costs, prev_tx_costs):
    region_dict = {}
    total_dict = {}

    region_dict["capacity"] = compare_capacity(year)
    if year == 2030:
        region_dict["capacity"] = add_coal_retirements(
            region_dict["capacity"],
            "No Policy",
            ["Coal Phaseout", "Coal Phaseout No New Gas"],
        )
    total_dict["capacity"] = (
        region_dict["capacity"].groupby(["Category", "Resource Name"]).sum()
    )

    region_dict["energy"] = compare_energy(year)
    total_dict["energy"] = region_dict["energy"].groupby("Resource Name").sum()

    region_dict["emissions"] = compare_emissions(year)
    total_dict["emissions"] = region_dict["emissions"].sum()
    total_dict["emissions"].name = "MT CO2"
    total_dict["emissions"].index.name = "Case"
    total_dict["emissions"] = total_dict["emissions"].reset_index()

    region_dict["network"] = compare_tx_build(year)
    total_dict["network"] = region_dict["network"].groupby("Case").sum()

    region_dict["spur_line"] = compare_spur_line_build(year)
    total_dict["spur_line"] = region_dict["spur_line"].groupby("Case").sum()

    region_dict["costs"] = compare_costs(year)
    if prev_spur_costs is None:
        region_dict["costs"]["prev_period_spur_line"] = 0
    else:
        prev_spur_costs = prev_spur_costs.groupby(["Case", "Region"]).sum()
        region_dict["costs"]["prev_period_spur_line"] = prev_spur_costs[
            "Spur Line Inv Cost"
        ]

    region_dict["costs"]["cTotal"] = region_dict["costs"][
        ["cFix", "cVar", "cNSE", "cStart", "prev_period_spur_line"]
    ].sum(axis=1)

    total_dict["costs"] = region_dict["costs"].groupby("Case").sum()
    # total_dict["costs"]["spur_line"] = total_dict["spur_line"]["Spur Line Inv Cost"]

    if prev_tx_costs is None:
        total_dict["costs"]["prev_period_transmission"] = 0
    else:
        total_dict["costs"]["prev_period_transmission"] = prev_tx_costs[
            "Cost_Trans_Capacity"
        ]

    total_dict["costs"]["current_period_transmission"] = total_dict["network"][
        "Cost_Trans_Capacity"
    ]
    total_dict["costs"]["cTotal"] = total_dict["costs"][
        [
            "cFix",
            "cVar",
            "cNSE",
            "cStart",
            "prev_period_spur_line",
            "prev_period_transmission",
            "current_period_transmission",
        ]
    ].sum(axis=1)

    region_dict["demand"] = compare_demand(year)
    total_dict["demand"] = region_dict["demand"].groupby("Case").sum()

    # total_dict["energy_cost"] = total_dict["costs"]["cTotal"] / total_dict["demand"]
    # total_dict["energy_cost"] = (
    #     total_dict["energy_cost"]
    #     .reset_index()
    #     .rename(columns={"index": "Case", 0: "Total Cost ($/MWh)"})
    # )

    return region_dict, total_dict


def make_tx_spur_fig(
    total_dict_2030,
    total_dict_2045,
    case_list,
    file_name,
    scale_factor=2,
    yaxis_title_font_size=14,
    xaxis_label_font_size=12,
    file_type="png",
):

    network_2030 = total_dict_2030["network"].reset_index()
    network_2030["Period"] = 2030
    network_2045 = total_dict_2045["network"].reset_index()
    network_2045["Period"] = 2045
    data = pd.concat([network_2030, network_2045])
    data["Cost_Trans_Capacity_Mil"] = data["Cost_Trans_Capacity"] / 1e6

    base_tx = alt.Chart(data.query("Case.isin(@case_list)")).encode(
        x=alt.X("Case", sort=case_list, axis=alt.Axis(title=None, labelFontSize=12)),
    )

    tx_distance = base_tx.mark_bar().encode(
        y=alt.Y(
            "New_Trans_Capacity:Q",
            axis=alt.Axis(
                title=["Transmission Expansion (MW-miles)"], titleFontSize=14
            ),
        ),
        color=alt.Color("Period:O", sort="descending"),
        order="Period",
    )

    tx_cost = base_tx.mark_circle(size=60, color="red", stroke="white").encode(
        y=alt.Y(
            "sum(Cost_Trans_Capacity_Mil):Q",
            axis=alt.Axis(title="Transmission Cost (Mil. $)", titleFontSize=14),
        ),
        #     color="Period"
    )

    spur_2030 = total_dict_2030["spur_line"].reset_index()
    spur_2030["Period"] = 2030
    spur_2045 = total_dict_2045["spur_line"].reset_index()
    spur_2045["Period"] = 2045
    data_spur = pd.concat([spur_2030, spur_2045])
    data_spur["Spur Line Inv Cost Million"] = data_spur["Spur Line Inv Cost"] / 1e6
    data_spur["Spur Line GW-Miles"] = data_spur["Spur Line MW-Miles"] / 1000

    base_spur = alt.Chart(data_spur.query("Case.isin(@case_list)")).encode(
        x=alt.X("Case", sort=case_list, axis=alt.Axis(title=None, labelFontSize=12)),
    )

    spur_distance = base_spur.mark_bar().encode(
        y=alt.Y(
            "Spur Line GW-Miles:Q",
            axis=alt.Axis(title=["Spur Line (GW-miles)"], titleFontSize=14),
        ),
        color=alt.Color("Period:O", sort="descending"),
        order="Period",
    )

    spur_cost = base_spur.mark_circle(size=60, color="red", stroke="white").encode(
        y=alt.Y(
            "sum(Spur Line Inv Cost Million):Q",
            axis=alt.Axis(title="Spur Line Cost (Mil. $)", titleFontSize=14),
        ),
    )

    (
        alt.layer(spur_distance, spur_cost).resolve_scale(y="independent")
        | alt.layer(tx_distance, tx_cost).resolve_scale(y="independent")
    ).configure_view(strokeWidth=0).configure_axis(grid=False).save(
        file_name, scale_factor=scale_factor, webdriver="firefox",
    )


def make_cap_change_fig(
    total_dict,
    case_list,
    file_name,
    scale_factor=2,
    yaxis_title_font_size=14,
    xaxis_label_font_size=12,
):
    chart_list = []
    for year, df_dict in total_dict.items():
        tidy_cap = make_data_tidy(
            df_dict["capacity"], "Capacity (MW)", ["Resource Name", "Category"]
        )
        data = tidy_cap.loc[
            tidy_cap.Category.isin(["New Capacity", "Retired Capacity"]), :
        ]
        data.loc[data.Category == "Retired Capacity", "Capacity (MW)"] *= -1
        data["idx"] = data["Resource Name"].map(RESOURCE_ORDER_DICT)

        chart = (
            alt.Chart(data.query("Case.isin(@case_list)"))
            .mark_bar()
            .encode(
                x=alt.X(
                    "Case",
                    sort=case_list,
                    axis=alt.Axis(title=None, labelFontSize=xaxis_label_font_size),
                ),
                y=alt.Y(
                    "Capacity (MW):Q",
                    axis=alt.Axis(
                        title="Capacity Change (MW)",
                        titleFontSize=yaxis_title_font_size,
                    ),
                ),
                color=RESOURCE_COLORS,
                order="idx",  # alt.Order("idx", sort="descending")
            )
            .properties(title=f"{year}")
        )

        chart_list.append(chart)

    alt.hconcat(*chart_list).configure_view(strokeWidth=0).configure_axis(
        grid=False
    ).resolve_scale(y="shared").save(
        file_name, scale_factor=scale_factor, webdriver="firefox",
    )


def make_tx_line_fig(
    region_dict,
    case_list,
    file_name=None,
    scale_factor=2,
    yaxis_title_font_size=14,
    xaxis_label_font_size=12,
):

    # Need to read a network file from first year to get starting tx capacity
    first_year = min(region_dict.keys())
    results_folder = find_results_folders(first_year)[0]
    input_folder = results_folder.parent / "Inputs"
    start_network = pd.read_csv(input_folder / "Network.csv")

    chart_tx_segments = region_dict[first_year]["network"].copy()
    # network df has a MultiIndex with levels Case and Path Name
    num_cases = len(chart_tx_segments.index.levels[0])
    start_tx_capacity = start_network["Line_Max_Flow_MW"].tolist() * num_cases

    chart_tx_segments.loc[:, "Transmission Capacity (MW)"] = start_tx_capacity
    chart_tx_segments["year"] = "Start"
    start_tx_capacity = chart_tx_segments["Transmission Capacity (MW)"].values

    df_list = [chart_tx_segments]
    for year, year_dict in region_dict.items():
        df = year_dict["network"]
        df.loc[:, "Transmission Capacity (MW)"] = (
            df.loc[:, "New_Trans_Capacity"] + start_tx_capacity
        )
        df["year"] = year

        # Set start_tx_capacity to new value for next planning period
        start_tx_capacity = df["Transmission Capacity (MW)"].values
        df_list.append(df)

    all_tx_segments = pd.concat(df_list)
    # return all_tx_segments

    chart = (
        alt.Chart(data=all_tx_segments.reset_index().query("Case.isin(@case_list)"))
        .mark_bar()
        .encode(
            x=alt.X(
                "Case:N",
                sort=case_list,
                axis=alt.Axis(title=None, labelFontSize=xaxis_label_font_size),
            ),
            y=alt.Y(
                "Transmission Capacity (MW)",
                axis=alt.Axis(titleFontSize=yaxis_title_font_size),
            ),
            color=alt.Color("Path Name:N", scale=alt.Scale(scheme="tableau20")),
        )
        .facet(column=alt.Column("year:O", sort=["Start"], title=None))
        .configure_view(strokeWidth=0)
        .configure_axis(
            # grid=False
        )
        .configure_header(labelFontSize=14)
    )

    if file_name is None:
        return chart
    else:
        chart.save(
            file_name, scale_factor=scale_factor, webdriver="firefox",
        )


def make_cost_co2_cap_energy_fig(
    total_dict,
    case_list,
    file_name,
    scale_factor=2,
    yaxis_title_font_size=14,
    xaxis_label_font_size=12,
):

    tidy_cap = make_data_tidy(
        total_dict["capacity"], "Capacity (MW)", ["Resource Name", "Category"]
    )
    tidy_cap["Capacity (GW)"] = tidy_cap["Capacity (MW)"] / 1000
    tidy_cap = tidy_cap.loc[tidy_cap["Category"] == "Final Capacity"]
    tidy_cap["idx"] = tidy_cap["Resource Name"].map(RESOURCE_ORDER_DICT)

    tidy_energy = make_data_tidy(total_dict["energy"], "Energy (MWh)")
    tidy_energy["idx"] = tidy_energy["Resource Name"].map(RESOURCE_ORDER_DICT)

    energy_cost_emissions = total_dict["energy_cost"].merge(
        total_dict["emissions"], on="Case"
    )
    energy_cost_emissions["GT CO2"] = energy_cost_emissions["MT CO2"] / 1000

    base = alt.Chart(energy_cost_emissions.query("Case.isin(@case_list)")).encode(
        x=alt.X(
            "Case",
            sort=case_list,
            axis=alt.Axis(title=None, labelFontSize=xaxis_label_font_size),
        )
    )

    emissions = base.mark_circle(size=60, color="red", stroke="white").encode(
        y=alt.Y(
            "GT CO2",
            axis=alt.Axis(
                title="CO\u2082 Emissions (GT)", titleFontSize=yaxis_title_font_size
            ),
        )
    )

    cost = base.mark_bar().encode(
        y=alt.Y(
            "Total Cost ($/MWh):Q",
            axis=alt.Axis(
                title="Total Cost ($/MWh)", titleFontSize=yaxis_title_font_size
            ),
        )
    )

    cost_emissions = alt.layer(cost, emissions).resolve_scale(y="independent")

    cap = (
        alt.Chart(tidy_cap.query("Case.isin(@case_list)"))
        .mark_bar()
        .encode(
            x=alt.X(
                "Case",
                sort=case_list,
                axis=alt.Axis(title=None, labelFontSize=xaxis_label_font_size),
            ),
            y=alt.Y(
                "Capacity (GW)", axis=alt.Axis(titleFontSize=yaxis_title_font_size)
            ),
            order="idx",
            color=RESOURCE_COLORS,
        )
    )

    energy_data = tidy_energy.loc[
        (tidy_energy.Case.isin(case_list))
        & ~(tidy_energy["Resource Name"].isin(["Pumped Hydro", "Battery"])),
        :,
    ]
    energy = (
        alt.Chart(energy_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "Case",
                sort=case_list,
                axis=alt.Axis(title=None, labelFontSize=xaxis_label_font_size),
            ),
            y=alt.Y(
                "Energy (MWh)",
                stack="normalize",
                axis=alt.Axis(
                    title="Energy Fraction", titleFontSize=yaxis_title_font_size
                ),
            ),
            order="idx",
            color=RESOURCE_COLORS,
        )
    )

    (cost_emissions | cap | energy).configure_view(strokeWidth=0).configure_axis(
        grid=False
    ).save(
        file_name, scale_factor=scale_factor, webdriver="firefox",
    )


def make_figures(total_dict, region_dict):

    for year, year_total in total_dict.items():
        make_cost_co2_cap_energy_fig(
            year_total, POLICY_ORDER, f"policy_cost_co2_cap_energy_{year}.png"
        )
        make_cost_co2_cap_energy_fig(
            year_total, SENSITIVITY_ORDER, f"sensitivity_cost_co2_cap_energy_{year}.png"
        )

    make_tx_spur_fig(
        total_dict[2030],
        total_dict[2045],
        POLICY_ORDER,
        "policy_transmission_spur_costs.png",
    )
    make_tx_spur_fig(
        total_dict[2030],
        total_dict[2045],
        SENSITIVITY_ORDER,
        "sensitivity_transmission_spur_costs.png",
    )

    make_cap_change_fig(total_dict, POLICY_ORDER, "policy_capacity_changes.png")
    make_cap_change_fig(
        total_dict, SENSITIVITY_ORDER, "sensitivity_capacity_changes.png"
    )

    make_tx_line_fig(region_dict, POLICY_ORDER, "policy_tx_expansion.png")
    make_tx_line_fig(region_dict, SENSITIVITY_ORDER, "sensitivity_tx_expansion.png")


def write_results_to_excel(total_dict, region_dict):

    with pd.ExcelWriter("WECC results.xlsx") as writer:
        for year, results_dict in total_dict.items():
            for key, df in results_dict.items():
                df.to_excel(writer, sheet_name=f"{key}_{year}")

    with pd.ExcelWriter("Regional results.xlsx") as writer:
        for year, results_dict in region_dict.items():
            for key, df in results_dict.items():
                df.to_excel(writer, sheet_name=f"{key}_{year}")


def calc_energy_cost(total_dict, region_dict, years):
    idx = pd.IndexSlice

    # This should probably be moved out of this function
    extra_az_costs = calc_all_costs()

    for year in years:
        total_dict[year]["energy_cost"] = total_dict[year]["costs"][["cTotal"]].merge(
            total_dict[year]["demand"], on="Case"
        )
        total_dict[year]["energy_cost"]["Total Cost ($/MWh)"] = (
            total_dict[year]["energy_cost"]["cTotal"]
            / total_dict[year]["energy_cost"]["Total Demand"]
        )
        total_dict[year]["energy_cost"].name = "Total Cost ($/MWh)"
        total_dict[year]["energy_cost"] = (
            total_dict[year]["energy_cost"].reset_index().round(2)
        )

        for case in extra_az_costs.index.levels[-1]:
            for col in [
                "Net Trade Costs",
                "RPS Costs",
                "CES Costs",
                "Total Extra Costs",
            ]:
                region_dict[year]["costs"].loc[
                    idx[case, "WECC_AZ"], col
                ] = extra_az_costs.loc[idx[year, case], col]

        component_cost_cols = ["cFix", "cVar", "cNSE", "cStart", "Total Extra Costs"]
        region_dict[year]["costs"]["Total Cost"] = (
            region_dict[year]["costs"].loc[:, component_cost_cols].sum(axis=1)
        )
        region_dict[year]["energy_cost"] = (
            region_dict[year]["costs"]["Total Cost"]
            / region_dict[year]["demand"]["Total Demand"]
        ).round(2)
        region_dict[year]["energy_cost"] = region_dict[year]["energy_cost"].loc[
            idx[:, "WECC_AZ"],
        ]

    return total_dict, region_dict


@app.command()
def main(figures: bool = True, excel: bool = True):

    years = find_years()
    # first_year = years[0]
    total_dict, region_dict = {}, {}

    prev_spur_costs = None
    prev_tx_costs = None
    for year in years:
        region_dict[year], total_dict[year] = build_results(
            year, prev_spur_costs, prev_tx_costs
        )
        prev_spur_costs = region_dict[year]["spur_line"]
        prev_tx_costs = total_dict[year]["network"]

    total_dict, region_dict = calc_energy_cost(total_dict, region_dict, years)

    if figures:
        make_figures(total_dict, region_dict)

    # Dictionaries should be built with year as the first set of keys based on folders.
    # I'm compiling this now but need to go back and fix.
    if excel:

        write_results_to_excel(total_dict, region_dict)


if __name__ == "__main__":
    app()
