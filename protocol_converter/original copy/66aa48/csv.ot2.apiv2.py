import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/66aa48/csv.ot2.apiv2.py"

from opentrons.types import Point

metadata = {
    'protocolName': 'CSV Consolidation',
    'author': 'Nick <protocols@opentrons.com>',
    'apiLevel': '2.13'
}


def run(ctx):

    [volume_of_each_mutant_to_transfer,
     pipette_mount,
     tip_strategy,
     inactive_CSV,
     decrease_CSV,
     no_change_CSV,
     increase_CSV] = get_values(  # noqa: F821
        'volume_of_each_mutant_to_transfer',
        'pipette_mount',
        'tip_strategy',
        'inactive_CSV',
        'decrease_CSV',
        'no_change_CSV',
        'increase_CSV')

    if volume_of_each_mutant_to_transfer < 5:
        raise Exception('Invalid volume selection.')

    # load labware
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '1',
        'source plate')
    dest_rack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
        '4',
        'Eppendorf tuberack for pools'
    )

    tips = ctx.load_labware('opentrons_96_tiprack_300ul', '2')
    p50 = ctx.load_instrument(
        'p50_single', mount=pipette_mount, tip_racks=[tips])

    # parse files and perform pooling
    touch = False if volume_of_each_mutant_to_transfer > 10 else True
    for csv, dest in zip(
            [inactive_CSV, decrease_CSV, no_change_CSV, increase_CSV],
            [well for well in dest_rack.wells()[:4]]
    ):
        sources = [source_plate.wells_by_name()[line.split(',')[0]]
                   for line in csv.splitlines() if line]
        d_offset = dest.bottom().move(Point(
            x=dest.diameter/2, y=0, z=dest.depth*0.9))
        if tip_strategy == 'one tip per pool':
            p50.pick_up_tip()
        for s in sources:
            if not p50.has_tip:
                p50.pick_up_tip()
            p50.transfer(
                volume_of_each_mutant_to_transfer,
                s,
                dest,
                new_tip='never'
            )
            if touch:
                p50.move_to(d_offset)
            p50.blow_out(dest.top())
            if tip_strategy == 'one tip per pool':
                p50.drop_tip()
        if p50.has_tip:
            p50.drop_tip()

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
    filename = f"detailed_action_json/66aa48.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)