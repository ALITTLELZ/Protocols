import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6b8c90-3/6b8c90-3.ot2.apiv2.py"

metadata = {
    'protocolName': 'EtOH 48 Sample to 1mL Vial',
    'author': 'Chaz <chaz@opentrons.com>',
    'apiLevel': '2.9'
}


def run(protocol):
    [mnt50, num_samps] = get_values(  # noqa: F821
     'mnt50', 'num_samps')

    # load labware
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', '7')
    p50 = protocol.load_instrument('p50_single', mnt50, tip_racks=[tips])

    v1ml = [
        protocol.load_labware(
            'custom1mltesttube_24_wellplate_5000ul',
            s) for s in ['2', '5']
            ]
    v1mls = [well for plate in v1ml for well in plate.wells()][:num_samps]

    v5ml = [
        protocol.load_labware(
            'custom5mltesttube_24_wellplate_5000ul',
            s) for s in ['1', '4']
            ]

    v5mls = [well for plate in v5ml for well in plate.wells()][:num_samps]

    for src, dest in zip(v5mls, v1mls):
        p50.pick_up_tip()
        p50.aspirate(50, src.bottom(40))
        p50.dispense(50, dest.bottom(20))
        p50.blow_out()
        p50.touch_tip(dest, v_offset=-2)
        p50.drop_tip()

    protocol.comment('Protocol complete!')

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
    filename = f"detailed_action_json/6b8c90-3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)