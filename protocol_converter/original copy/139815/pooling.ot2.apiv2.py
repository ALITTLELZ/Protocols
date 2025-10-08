import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/139815/pooling.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'Pooling and Consolidation',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    p10_mount, p300_mount = get_values(  # noqa: F821
        'p10_mount', 'p300_mount')

    # load labware
    plate = ctx.load_labware(
        'eppendorftwin.tec96_96_aluminumblock_200ul',
        '1',
        '96-well plate in insert'
    )
    strips = ctx.load_labware(
        'usascientific8strip_96_aluminumblock_300ul', '2', 'strips in insert')
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '3',
        '1.5ml tuberack'
    )
    tiprack10 = [ctx.load_labware(
        'opentrons_96_filtertiprack_10ul', '4', '10ul tiprack')]
    tiprack300 = [ctx.load_labware(
        'opentrons_96_filtertiprack_200ul', '5', '300ul tiprack')]

    # pipettes
    m10 = ctx.load_instrument(
        'p10_multi', mount=p10_mount, tip_racks=tiprack10)
    p300 = ctx.load_instrument(
        'p300_single', mount=p300_mount, tip_racks=tiprack300)

    # reagents
    strip = strips.columns()[0]
    pool = tuberack.wells()[0]

    # consolidate plate contents to 1 strip
    for well in plate.rows()[0]:
        m10.pick_up_tip()
        m10.aspirate(2, well.top())
        m10.aspirate(2, well.bottom(2))
        m10.dispense(4, strip[0].bottom(2))
        m10.blow_out(strip[0].bottom(5))
        m10.drop_tip()

    ctx.pause('Spin down the strip and return to the OT-2 for pooling.')

    p300.consolidate(
        24, [well.bottom(1) for well in strip], pool.bottom(5), blow_out=True)

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
    filename = f"detailed_action_json/139815.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)