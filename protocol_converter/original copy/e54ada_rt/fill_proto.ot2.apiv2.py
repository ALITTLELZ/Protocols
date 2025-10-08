import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/e54ada_rt/fill_proto.ot2.apiv2.py"

"""OPENTRONS."""
metadata = {
    'protocolName': 'Reverse Transcriptase Preparation',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):
    """PROTOCOL."""
    [num_samp, reag_vol, well_plate,
        p20_mount] = get_values(  # noqa: F821
        "num_samp", "reag_vol", "well_plate",
            "p20_mount")
    num_tubes = num_samp+1
    if not 1 <= num_samp <= 95:
        raise Exception("Enter sample number 1-95")

    # load labware
    sample_plate = ctx.load_labware(well_plate, 3)
    tuberacks = [ctx.load_labware('opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', slot)  # noqa: E501
                 for slot in [4, 1, 5, 2]]

    all_tubes = [tube for tuberackset in [tuberacks[:2], tuberacks[2:]]
                 for i in range(6)
                 for j in range(2)
                 for tube in tuberackset[j].columns()[i]][:num_tubes]

    primer_tubes = all_tubes[:-1]

    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in [7, 8, 9]]

    # load instrument
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tipracks)

    mix_tube = all_tubes[-1]
    p20.flow_rate.aspirate = 7.56
    p20.flow_rate.dispense = 7.56
    # add mix
    ctx.comment('\n~~~~~~~~~~~~~~~ADDING MIX~~~~~~~~~~~~~~~~~\n')
    p20.flow_rate.aspirate /= 2
    p20.flow_rate.dispense /= 2
    for well in sample_plate.wells()[:num_samp]:
        p20.pick_up_tip()
        p20.aspirate(reag_vol, mix_tube)
        p20.dispense(reag_vol, well)
        p20.mix(1, reag_vol, well)
        p20.blow_out()
        p20.drop_tip()
        ctx.comment('\n')

    # add primer
    ctx.comment('\n~~~~~~~~~~~~~~~ADDING PRIMER~~~~~~~~~~~~~~\n')
    for tube, well in zip(primer_tubes, sample_plate.wells()):
        p20.pick_up_tip()
        p20.aspirate(1, tube, rate=0.5)
        p20.dispense(1, well, rate=0.5)
        p20.mix(1, 1, well)
        p20.blow_out()
        p20.drop_tip()

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
    filename = f"detailed_action_json/e54ada_rt.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)