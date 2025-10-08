import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/checkit/checkit.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Next Advance Checkit Go',
    'author': 'Nick <protocols@opentrons.com>',
    'apiLevel': '2.11'
}


def run(ctx):

    [lw_checkit, pipette_type, pipette_mount] = get_values(  # noqa: F821
        'lw_checkit', 'pipette_type', 'pipette_mount')

    tiprack_map = {
        'p20_single_gen2': 'opentrons_96_tiprack_20ul',
        'p300_single_gen2': 'opentrons_96_tiprack_300ul',
        'p20_multi_gen2': 'opentrons_96_tiprack_20ul',
        'p300_multi_gen2': 'opentrons_96_tiprack_300ul'
    }

    checkit_map = {
        'checkit_8_wellplate_2ul': {
            'FLOW_RATE_ASPIRATE': 7.6,  # ul/s
            'FLOW_RATE_DISPENSE': 15,  # ul/s
            'FLOW_RATE_BLOWOUT': 15,  # ul/s
            'BLOWOUT_HEIGHT': 3.0,  # mm above bottom of well
            'VOLUME': 2.0,  # ul
            'BLOWOUT': True,
            'DROP': True
        },
        'checkit_8_wellplate_5ul': {
            'FLOW_RATE_ASPIRATE': 7.6,  # ul/s
            'FLOW_RATE_DISPENSE': 15,  # ul/s
            'FLOW_RATE_BLOWOUT': 15,  # ul/s
            'BLOWOUT_HEIGHT': 3.0,  # mm above bottom of well
            'VOLUME': 5.0,  # ul
            'BLOWOUT': True,
            'DROP': True
        },
        'checkit_8_wellplate_10ul': {
            'FLOW_RATE_ASPIRATE': 7.6,  # ul/s
            'FLOW_RATE_DISPENSE': 15,  # ul/s
            'FLOW_RATE_BLOWOUT': 15,  # ul/s
            'BLOWOUT_HEIGHT': 4.0,  # mm above bottom of well
            'VOLUME': 10.0,  # ul
            'BLOWOUT': True,
            'DROP': True
        },
        'checkit_8_wellplate_20ul': {
            'FLOW_RATE_ASPIRATE': 7.6,  # ul/s
            'FLOW_RATE_DISPENSE': 15,  # ul/s
            'FLOW_RATE_BLOWOUT': 15,  # ul/s
            'BLOWOUT_HEIGHT': 3.0,  # mm above bottom of well
            'VOLUME': 20.0,  # ul
            'BLOWOUT': True,
            'DROP': True
        },
        'checkit_8_wellplate_50ul': {
            'FLOW_RATE_ASPIRATE': 94,  # ul/s
            'FLOW_RATE_DISPENSE': 94,  # ul/s
            'FLOW_RATE_BLOWOUT': 94,  # ul/s
            'BLOWOUT_HEIGHT': 5.0,  # mm above bottom of well
            'VOLUME': 50.0,  # ul
            'BLOWOUT': True,
            'DROP': True
        }
    }

    # load tipracks
    tiprack_type = tiprack_map[pipette_type]
    tiprack = [ctx.load_labware(tiprack_type, '5')]

    checkit_params = checkit_map[lw_checkit]
    cartridge = ctx.load_labware(lw_checkit, '2')

    # load pipette
    pip = ctx.load_instrument(pipette_type, pipette_mount, tip_racks=tiprack)

    # check volume
    if checkit_params['VOLUME'] < pip.min_volume:
        ctx.pause(f'WARNING: Cartridge volume ({checkit_params["VOLUME"]}) is  below tested pipette volume ({pip.min_volume}). Proceed?')
    if checkit_params['VOLUME'] > pip.max_volume:
        ctx.pause(f'WARNING: Cartridge volume ({checkit_params["VOLUME"]}) is  below tested pipette volume ({pip.max_volume}). Proceed?')

    # set rates
    pip.flow_rate.aspirate = checkit_params['FLOW_RATE_ASPIRATE']
    pip.flow_rate.dispense = checkit_params['FLOW_RATE_DISPENSE']
    pip.flow_rate.blow_out = checkit_params['FLOW_RATE_BLOWOUT']
    ctx.max_speeds['A'] = 100
    ctx.max_speeds['X'] = 100
    ctx.max_speeds['Y'] = 100
    ctx.max_speeds['Z'] = 100

    # transfer
    wells = cartridge.wells()[:(9-pip.channels)]
    num_aspirations = math.ceil(checkit_params['VOLUME']/pip.max_volume)
    vol_per_aspiration = round(checkit_params['VOLUME']/num_aspirations, 2)
    for i, well in enumerate(wells):
        pip.pick_up_tip()
        for _ in range(num_aspirations):
            pip.aspirate(vol_per_aspiration,
                         cartridge.wells_by_name()['A2'].bottom(2))
            pip.dispense(vol_per_aspiration, well.bottom(1))
            if checkit_params['BLOWOUT']:
                pip.blow_out(well.bottom(checkit_params['BLOWOUT_HEIGHT']))
        if checkit_params['DROP']:
            pip.drop_tip()
        else:
            pip.return_tip()

        if i < len(wells) - 1:
            ctx.pause('Please flip cartridge tab. Resume once measurement  is read.')
        else:
            ctx.comment('Please flip cartridge tab.')

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
    filename = f"detailed_action_json/checkit.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)