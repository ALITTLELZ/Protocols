import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/09cdbe/cherrypick.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'Consolidation from .csv',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    plate_type, p20_mount, transfer_csv = get_values(  # noqa: F821
        'plate_type', 'p20_mount', 'transfer_csv')

    # load labware
    source_plates = {
        str(i+1): ctx.load_labware(plate_type, slot, 'plate ' + str(i+1))
        for i, slot in enumerate(['2', '5', '8', '11', '6'])
    }
    tuberack = ctx.load_labware(
        'vwr_15_tuberack_5000ul', '9', 'pooling tuberack')
    tipracks = [
        ctx.load_labware('opentrons_96_tiprack_20ul', slot, '20µl tiprack')
        for slot in ['1', '4', '7', '10', '3']
    ]

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
        slot, well, tube, volume = line[:4]
        source = source_plates[slot].wells_by_name()[parse_well(well)]
        destination_tube = tuberack.wells_by_name()[parse_well(tube)]
        vol = float(volume)
        air_vol = (20-vol)/2
        p20.pick_up_tip()
        p20.aspirate(air_vol, source.top())
        p20.aspirate(vol, source)
        p20.aspirate(air_vol, source.top(-1))
        p20.touch_tip(source)
        p20.dispense(20, destination_tube)
        p20.blow_out(destination_tube.bottom(2))
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
    filename = f"detailed_action_json/09cdbe.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)