import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7062c9-aliquot/aliquot.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Aliquot',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.13'
    }


def run(ctx):
    [num_aliquots, vol_aliquot, lw_source, type_pip,
     mount_pip] = get_values(  # noqa: F821
        'num_aliquots', 'vol_aliquot', 'lw_source', 'type_pip', 'mount_pip')

    # labware
    num_racks = math.ceil(num_aliquots/24)
    dest_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', slot,
            f'rack {i+1}')
        for i, slot in enumerate(['4', '5', '1', '2'][:num_racks])]
    source = ctx.load_labware(lw_source, '6', 'source (A1)').wells()[0]

    pip = ctx.load_instrument(type_pip, mount_pip)

    tiprack = [
        ctx.load_labware(f'opentrons_96_tiprack_{pip.max_volume}ul', '3')]
    pip.tip_racks = tiprack

    def slow_withdraw(well, pip=pip, delay_seconds=2.0):
        pip.default_speed /= 10
        if delay_seconds > 0:
            ctx.delay(seconds=delay_seconds)
        pip.move_to(well.top())
        pip.default_speed *= 10

    aliquots = [
        well for rack in dest_racks for well in rack.wells()][:num_aliquots]
    pip.pick_up_tip()
    for a in aliquots:
        pip.aspirate(vol_aliquot, source.bottom(3))
        slow_withdraw(source)
        pip.dispense(vol_aliquot, a.bottom(2))
        slow_withdraw(a)
    pip.drop_tip()

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
    filename = f"detailed_action_json/7062c9-aliquot.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)