import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/776039/cherrypick.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'Consolidation from .csv',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    p20_mount, transfer_csv = get_values(  # noqa: F821
        'p20_mount', 'transfer_csv')

    # load labware
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '2',
        '1.5ml tuberack')
    tipracks = [
        ctx.load_labware('opentrons_96_tiprack_20ul', '1', '20ul tiprack')]

    destination_tube = tuberack.wells()[0]

    # load pipette
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tipracks)

    # parse .csv
    transfer_info = [
        [val.strip() for val in line.split(",")]
        for line in transfer_csv.splitlines()[1:] if line
    ]

    def parse_well(well_name):
        return well_name[0].upper() + str(int(well_name[1:]))

    # perform transfers
    for line in transfer_info:
        well, volume = [line[1], line[3]]
        source = tuberack.wells_by_name()[parse_well(well)]
        vol = float(volume)
        p20.pick_up_tip()
        if vol <= 17:
            p20.aspirate(2, source.top())
        p20.aspirate(vol, source)
        if vol <= 19:
            p20.air_gap(1)
        p20.dispense(p20.current_volume, destination_tube)
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
    filename = f"detailed_action_json/776039.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)