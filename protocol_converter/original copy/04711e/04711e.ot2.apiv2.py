import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/04711e/04711e.ot2.apiv2.py"

# flake8: noqa

import math

metadata = {
    'protocolName': 'PCR Prep',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [num_samp,
      p300_mount, m20_mount] = get_values(  # noqa: F821
      "num_samp", "p300_mount", "m20_mount")

    # num_samp = 16
    # p300_mount = 'left'
    # m20_mount = 'right'

    # labware
    tuberack = ctx.load_labware('opentrons_24_tuberack_2000ul', 4)

    source_plate = ctx.load_labware('pcrplate_96_wellplate_200ul', 1)
    middle_plate = ctx.load_labware('pcrplate_96_wellplate_200ul', 2)
    final_plate = ctx.load_labware('pcrplate_96_wellplate_200ul', 3)

    tip300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
              for slot in [6]]
    tip20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
               for slot in [10, 11]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tip300)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                                tip_racks=tip20)

    # mapping
    mmx = tuberack['A1']
    primer = tuberack['A2']
    final_mmx = tuberack['A3']
    num_col = math.ceil(num_samp/8)

    # protocol
    ctx.comment('\n---------------MAKING MASTERMIX----------------\n\n')
    mmx_vol = 9.1
    primer_vol = 5.57

    p300.pick_up_tip()
    p300.transfer(mmx_vol*num_samp*1.15, mmx, final_mmx, new_tip='never')
    p300.drop_tip()

    total_vol = num_samp*(primer_vol+mmx_vol)
    p300.pick_up_tip()
    p300.transfer(primer_vol*num_samp*1.15, primer, final_mmx, new_tip='never')
    for _ in range(20):
        p300.aspirate(total_vol if total_vol < 300 else 300, final_mmx)
        p300.dispense(total_vol if total_vol < 300 else 300, final_mmx.top(z=-3))
    p300.mix(20, total_vol if total_vol < 300 else 300, final_mmx)
    p300.drop_tip()

    vol_per_col_well = (mmx_vol+primer_vol)*12*1.1
    p300.pick_up_tip()
    for well in middle_plate.columns()[0]:
        p300.aspirate(vol_per_col_well, final_mmx)
        p300.dispense(vol_per_col_well, well)
    p300.drop_tip()

    ctx.comment('\n---------------DISTRIBUTING MASTERMIX----------------\n\n')
    m20.pick_up_tip()
    for col in final_plate.rows()[0][:num_col]:
        m20.aspirate(14.7, middle_plate.rows()[0][0])
        m20.dispense(14.7, col)
    m20.drop_tip()

    ctx.comment('\n---------------DISTRIBUTING SAMPLE----------------\n\n')
    for s, d in zip(source_plate.rows()[0][:num_col], final_plate.rows()[0]):
        m20.pick_up_tip()
        m20.aspirate(4, s)
        m20.dispense(4, d)
        m20.mix(5, 15, d)
        m20.drop_tip()

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
    filename = f"detailed_action_json/04711e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)