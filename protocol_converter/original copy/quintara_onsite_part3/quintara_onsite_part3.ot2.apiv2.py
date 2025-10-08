import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/quintara_onsite_part3/quintara_onsite_part3.ot2.apiv2.py"

metadata = {
    'protocolName': 'Mastermix Filling 9 Plates',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [starting_tip_col, reag, source_labware, num_rounds,
        p20_mount, p300_mount] = get_values(  # noqa: F821
        "starting_tip_col", "reag", "source_labware", "num_rounds",
            "p20_mount", "p300_mount")

    # start of protocol
    reag_dict = {

        "synth1_columns": [0, 2],
        "synth1_vol": 14,
        "synth1_num_disp": 1,

        "screen10_columns": [2, 4],
        "screen10_vol": 10,
        "screen10_num_disp": 1,

        "seq5_columns": [4, 6],
        "seq5_vol": 8,
        "seq5_num_disp": 2,

        "lba_columns": [6, 8],
        "lba_vol": 30,
        "lba_num_disp": 6,

        "lbk_columns": [8, 10],
        "lbk_vol": 30,
        "lbk_num_disp": 6,

        "pcr_columns": [10, 12],
        "pcr_vol": 20,
        "pcr_num_disp": 9

    }

    reag_cols = reag_dict[reag + "_columns"]
    reag_vol = reag_dict[reag + "_vol"]
    reag_num_disp = reag_dict[reag + "_num_disp"]

    # labware
    source_plate = ctx.load_labware(source_labware, 11)
    dest_plates = [ctx.load_labware('doublepcr_96_wellplate_300ul', slot)
                   for slot in [7, 8, 9, 4, 5, 6, 1, 2, 3]]
    tips = [ctx.load_labware(
            'opentrons_96_tiprack_20ul' if reag_vol < 20 else
            'opentrons_96_filtertiprack_200ul', slot)
            for slot in [10]]

    starting_tip = tips[0].rows()[0][starting_tip_col-1]

    ctx.pause(f"""
    Ensure that there is a {tips[0]}.
    Select "Resume" on the Opentrons app.
        """)

    # pipettes
    pip = ctx.load_instrument('p20_multi_gen2' if reag_vol < 20 else
                              'p300_multi_gen2',
                              "right" if reag_vol < 20 else "left",
                              tip_racks=tips)

    all_dest_columns = [
                        col
                        for plate in dest_plates
                        for col in plate.rows()[0]
                        ]

    # source mapping
    reag_start_col = reag_cols[0]
    reag_end_col = reag_cols[1]

    source_cols = source_plate.rows()[0][
                                         reag_start_col:reag_end_col
                                         ]*1000

    src_col_ctr = 0
    disp_vol = 1 if reag_vol < 20 else 20

    for _ in range(num_rounds):
        if reag_num_disp > 1:
            all_chunks = [all_dest_columns[i:i+reag_num_disp]
                          for i in range(0, len(all_dest_columns),
                                         reag_num_disp)]

            if not pip.has_tip:
                pip.pick_up_tip(starting_tip)

            for chunk in all_chunks:
                source = source_cols[src_col_ctr]
                pip.aspirate(reag_vol*len(chunk)+disp_vol, source)
                src_col_ctr += 1
                for well in chunk:
                    pip.dispense(reag_vol, well.bottom(z=1))
                pip.dispense(disp_vol, source)
                ctx.comment('\n')
        else:
            if not pip.has_tip:
                pip.pick_up_tip(starting_tip)
            for source, dest in zip(source_cols, all_dest_columns):
                pip.aspirate(reag_vol, source)
                pip.dispense(reag_vol, dest.bottom(z=1))
                ctx.comment('\n')
        ctx.pause("Select Resume for another round")

    from opentrons.protocol_api.labware import Well, Labware
    import re
    import json
    all_vars = locals()

    # Wells that have been processed 
    processed_wells = set()
    liquid_locations = {}

    for var_name, var_value in all_vars.items():
        if isinstance(var_value, list) and len(var_value) > 0 and isinstance(var_value[0], Well):
            for i, well in enumerate(var_value):
                processed_wells.add(well)   
                display_name = well.display_name
                well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
                slot_match = re.search(r" on (\d+)$", display_name)
                slot_number = slot_match.group(1) if slot_match else "unknown"
                name_with_index = f"{var_name}[{i}]"
                liquid_locations[name_with_index] = {
                    "well": well_position,
                    "slot": slot_number
                }

    for var_name, var_value in all_vars.items():
        if isinstance(var_value, Well):
            if var_value in processed_wells:
                continue
            
            display_name = var_value.display_name
            well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
            slot_match = re.search(r" on (\d+)$", display_name)
            slot_number = slot_match.group(1) if slot_match else "unknown"
            liquid_locations[var_name] = {
                "well": well_position,
                "slot": slot_number
            }
    filename = f"detailed_action_json/quintara_onsite_part3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)