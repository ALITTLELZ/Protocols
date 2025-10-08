import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/158d42/1584d2.ot2.apiv2.py"

from opentrons import protocol_api


metadata = {
    'protocolName': 'RNA Normalization I & II',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):

    [
     _num_samp,
     _use_temp_mod,
     _p300_mount,

    ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "_num_samp",
        "_use_temp_mod",
        "_p300_mount")

    # VARIABLES

    # number of samples running (not including controls)
    num_samp = _num_samp

    # use temperature module or not
    use_temp_mod = _use_temp_mod

    # change pipette mounts here to "left" or "right", respectively
    p300_mount = _p300_mount

    # MODULES
    if use_temp_mod:
        temp_mod = ctx.load_module('temperature module gen2', '1')
        temp_mod.set_temperature(20)
        plate = temp_mod.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    else:
        plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '1')

    # LABWARE
    prl_tuberacks = [ctx.load_labware(
                 'nest_32_tuberack_8x5ml_8x5ml_8x5ml_8x5ml',
                 slot, label='sample tuberack')
                 for slot in ['7', '4']]

    reagent_tuberacks = [ctx.load_labware(
                    'opentrons_24_tuberack_nest_1.5ml_screwcap',
                    slot, label='rack') for slot in ['6', '3']]

    # TIPRACKS
    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '10')]

    # INSTRUMENTS
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tipracks)

    # MAPPING
    prl_rows = [tube
                for rack in prl_tuberacks
                for row in rack.rows()
                for tube in row][:num_samp]
    reagent_tubes = [tube
                     for rack in reagent_tuberacks
                     for row in rack.rows()
                     for tube in row][2:]
    negative_ctrl = plate.wells()[0]
    neg_ctrl_tube = reagent_tuberacks[0].wells()[0]
    positive_ctrl_1 = plate.rows()[0][11]
    pos_ctrl_tube = reagent_tuberacks[0].rows()[0][1]
    positive_ctrl_final = plate.wells()[1]
    plate_wells = [well for col in plate.columns()[::2] for well in col][2:]

    # protocol
    ctx.comment('\n\nMOVING NEGATIVE CONTROL TO PLATE\n')
    p300.pick_up_tip()
    p300.aspirate(50, neg_ctrl_tube.bottom(2))
    p300.dispense(30, negative_ctrl.bottom(negative_ctrl.depth/2))
    p300.dispense(20, negative_ctrl)
    p300.mix(5, 40, negative_ctrl)
    p300.drop_tip(ctx.loaded_labwares[12].wells()[0].top(z=-25))

    ctx.comment('\n\nMOVING SAMPLES TO PLATE\n')
    for prl_source, dest1, final_dest in zip(prl_rows,
                                             reagent_tubes,
                                             plate_wells):
        p300.pick_up_tip()
        p300.aspirate(50, prl_source.bottom(prl_source.depth/2))
        p300.dispense(50, dest1.bottom(2))
        p300.mix(5, 50, dest1.bottom(2))
        p300.aspirate(50, dest1.bottom(2))
        p300.dispense(30, final_dest.bottom(final_dest.depth/2))
        p300.dispense(20, final_dest)
        p300.mix(5, 40, final_dest)
        p300.drop_tip(ctx.loaded_labwares[12].wells()[0].top(z=-25))
        ctx.comment('\n')

    ctx.comment('\n\nMOVING POSITIVE CONTROL TO PLATE\n')
    pos_ctrl_aspiration_height = 0.4
    p300.pick_up_tip()
    p300.aspirate(50, pos_ctrl_tube.bottom(2))
    p300.dispense(30, positive_ctrl_1.bottom(positive_ctrl_1.depth/2))
    p300.dispense(20, positive_ctrl_1)
    p300.mix(5, 40, positive_ctrl_1)
    p300.aspirate(50, positive_ctrl_1.bottom(pos_ctrl_aspiration_height),
                  rate=0.5)

    p300.move_to(positive_ctrl_1.top(20))
    ctx.delay(seconds=2)

    p300.dispense(30, positive_ctrl_final.bottom(positive_ctrl_1.depth/2))
    p300.dispense(20, positive_ctrl_final)
    p300.mix(5, 40, positive_ctrl_final)
    p300.drop_tip(ctx.loaded_labwares[12].wells()[0].top(z=-25))

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
    filename = f"detailed_action_json/158d42.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)