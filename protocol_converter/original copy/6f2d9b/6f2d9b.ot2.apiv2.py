import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6f2d9b/6f2d9b.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'COVID-19 Patient Sample Prep',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [p1000_mount, extraction_type, samples,
        sample_vol, sample_air_gap] = get_values(  # noqa: F821
        "p1000_mount", "extraction_type", "samples", "sample_vol",
        "sample_air_gap")

    if extraction_type == "single":
        if not 1 <= samples <= 94:
            raise Exception('''Please enter a sample number between 1
                            and 94 for single extraction.''')
    elif extraction_type == "double":
        if not 1 <= samples <= 47:
            raise Exception('''Please enter a sample number between
                            1 and 47 for double extraction.''')

    def pick_up(pip):
        """Function that can be used instead of .pick_up_tip() that will pause
        robot when robot runs out of tips, prompting user to replace tips
        before resuming"""
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            ctx.pause("Please replace the empty tip rack.")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # Load Labware
    dwp = ctx.load_labware('kingfisher_96_deepwell_plate_2ml', 2)
    tuberacks = [ctx.load_labware('iclean_15_tuberack', slot)
                 for slot in range(4, 11)]
    tiprack_1000ul = ctx.load_labware('opentrons_96_filtertiprack_1000ul', 1)

    # Load Pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=[tiprack_1000ul])

    # Get sample and tube rack wells
    if extraction_type == "single":
        sample_wells = dwp.wells()[:samples]
        tube_wells = [well for rack in tuberacks
                      for well in rack.wells()][:samples]
    elif extraction_type == "double":
        sample_wells = dwp.wells()[:samples*2]
        tube_wells = [well for rack in tuberacks for well in rack.wells()
                      for _ in range(2)][:samples*2]

    # Transfer Patient Samples to each well
    for source, dest in zip(tube_wells, sample_wells):
        pick_up(p1000)
        p1000.aspirate(sample_vol, source)
        p1000.air_gap(sample_air_gap)
        p1000.dispense(sample_vol+sample_air_gap, dest)
        p1000.drop_tip()

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
    filename = f"detailed_action_json/6f2d9b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)