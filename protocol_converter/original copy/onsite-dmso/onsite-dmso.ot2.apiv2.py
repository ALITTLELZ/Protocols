import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/onsite-dmso/onsite-dmso.ot2.apiv2.py"

# flake8: noqa


metadata = {
    'protocolName': 'Diluting Samples with DMSO',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [csv, tubes_on_slot4, slot_2_height, slot_2_touch,
        slot_5_touch, p1000_mount] = get_values(  # noqa: F821
        "csv", "tubes_on_slot4", "slot_2_height", "slot_2_touch",
            "slot_5_touch", "p1000_mount")

    all_rows = [[val.strip() for val in line.split(',')]
                for line in csv.splitlines()
                if line.split(',')[0].strip()][1:]

    # labware
    res = ctx.load_labware('nest_1_reservoir_195ml', 1)
    tiprack = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 6)
    final_96_plate = ctx.load_labware('micronic_96_wellplate_1000ul', 5)
    middle_48_plate = ctx.load_labware("altemislab_48_wellplate_2000ul", 2)
    sample_racks = ctx.load_labware(tubes_on_slot4, 4)

    # pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=[tiprack])



    # protocol
    sample_tubes = [tube for tube in sample_racks.wells()]
    for i, row in enumerate(all_rows):
        vol = float(row[5])
        p1000.transfer(vol, res.wells()[0], sample_tubes[i].bottom(z=2), new_tip='always', air_gap=30, blow_out=True, blowout_location='destination well')
        p1000.pick_up_tip()
        p1000.mix(10, vol if vol < 1000 else 1000, sample_tubes[i].bottom(z=2))
        p1000.blow_out(sample_tubes[i].top(z=-1))
        p1000.drop_tip()

    ctx.pause("Check to see if powder has dissolved in DMSO")
    ctx.comment('\n\n\n')
    airgap = 30

    for i, row in enumerate(all_rows):
        vol = float(row[5])
        p1000.pick_up_tip()
        p1000.transfer(vol+100,
                       sample_tubes[i].bottom(z=2),
                       middle_48_plate.wells()[i].bottom(slot_2_height),
                       new_tip='never',
                       air_gap=30)

        p1000.aspirate(200, middle_48_plate.wells()[i].bottom(slot_2_height))
        p1000.air_gap(airgap)
        p1000.touch_tip(v_offset=-slot_2_touch)
        p1000.dispense(200+airgap, final_96_plate.wells()[i].top(z=-5))
        p1000.blow_out()
        p1000.touch_tip(v_offset=-slot_5_touch)
        p1000.drop_tip()
        ctx.comment('\n')

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
    filename = f"detailed_action_json/onsite-dmso.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)