import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/sci-phytip-protein-puri/sci-phytip-protein-puri.ot2.apiv2.py"

# flake8: noqa

metadata = {
    'protocolName': 'Phytip Protein A, ProPlus, ProPlus LX Columns - Protein Purification',
    'author': '',
    'source': '',
    'apiLevel': '2.11'
}



def run(ctx):

    [num_samp, m300_mount] = get_values(  # noqa: F821
    "num_samp", "m300_mount")

    # liquid volume uL - Max. 200
    VOL_EQL = 200
    VOL_SAMPLE = 200
    VOL_WASH1 = 200
    VOL_WASH2 = 200
    VOL_ELN = 80

    CYCLES_EQL = 4
    CYCLES_SAMPLE = 8
    CYCLES_WASH1 = 2
    CYCLES_WASH2 = 2
    CYCLES_ELN = 4

    # pipet flow rate uL/s
    FLOWRATE_EQL = 4
    FLOWRATE_SAMPLE = 4
    FLOWRATE_WASH1 = 8
    FLOWRATE_WASH2 = 8
    FLOWRATE_ELN = 4

    total_cols = int(num_samp//8)
    r1 = int(num_samp%8)
    if r1 != 0: total_cols = total_cols + 1


    # load labware and pipette
    phytiprack = ctx.load_labware('phytips_in_opentrons_box_96_300ul', '3', '300ul resin tiprack')

    sample_plate = ctx.load_labware('thermoscientific_96_wellplate_v_450', '2', 'samples plate')
    equilibration_plate = ctx.load_labware('thermoscientific_96_wellplate_v_450', '9', 'equilibration plate')
    wash1_plate = ctx.load_labware('thermoscientific_96_wellplate_v_450', '5', 'wash plate 1')
    wash2_plate = ctx.load_labware('thermoscientific_96_wellplate_v_450', '7', 'wash plate 2')
    elution_plate = ctx.load_labware('thermoscientific_96_wellplate_v_450', '11', 'elute plate')

    sample = sample_plate.rows()[0][:total_cols]
    eql = equilibration_plate.rows()[0][:total_cols]
    wash1 = wash1_plate.rows()[0][:total_cols]
    wash2 = wash2_plate.rows()[0][:total_cols]
    eln = elution_plate.rows()[0][:total_cols]

    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=[phytiprack])

    # mix sequences
    def plate_mix(cycles, volume, loc, rate, delay=20):
        m300.flow_rate.aspirate = rate
        m300.flow_rate.dispense = rate
        for _ in range(cycles):
            m300.aspirate(volume, loc.bottom(1.5))
            ctx.delay(seconds=delay)
            m300.dispense(volume, loc.bottom(1.5))
            ctx.delay(seconds=5)

    # perform
    for col in range(total_cols):
        tip_loc = phytiprack.rows()[0][col]
        m300.pick_up_tip(tip_loc)
        plate_mix(CYCLES_EQL, VOL_EQL*0.9, eql[col], FLOWRATE_EQL)
        plate_mix(CYCLES_SAMPLE, VOL_SAMPLE*0.9, sample[col], FLOWRATE_SAMPLE)
        plate_mix(CYCLES_WASH1, VOL_WASH1*0.9, wash1[col], FLOWRATE_WASH1)
        plate_mix(CYCLES_WASH2, VOL_WASH2*0.9, wash2[col], FLOWRATE_WASH2)
        plate_mix(CYCLES_ELN, VOL_ELN+50, eln[col], FLOWRATE_ELN)
        m300.return_tip()

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
    filename = f"detailed_action_json/sci-phytip-protein-puri.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)