import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6d901d/6d901d.ot2.apiv2.py"

# flake8: noqa
from opentrons import protocol_api
from opentrons.types import Mount

metadata = {
    'protocolName': 'Normalization with a multi-channel pipette  used as a single-channel pipette',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.12'
    }


def transpose_matrix(m):
    return [[r[i] for r in reversed(m)] for i in range(len(m[0]))]

def flatten_matrix(m):
    """ Converts a matrix to a 1D array, e.g. [[1,2],[3,4]] -> [1,2,3,4]
    """
    return [cell for row in m for cell in row]


def well_csv_to_list(csv_string):
    """
    Takes a csv string and flattens to a list, re-ordering to match
    Opentrons well order convention (A1, B1, C1, ..., A2, B2, B2, ...)
    """
    data = [
        line.split(',')
        for line in reversed(csv_string.split('\n')) if line.strip()
        if line
    ]
    if len(data[0]) > len(data):
        # row length > column length ==> "landscape", so transpose
        return flatten_matrix(transpose_matrix(data))
    # "portrait"
    return flatten_matrix(data)


def run(ctx: protocol_api.ProtocolContext):
    [volumes_csv,
     p300_mount,
     p20_mount,
     plate_type,
     res_type,
     filter_tip,
     tip_reuse] = get_values(  # noqa: F821
     "volumes_csv",
     "p300_mount",
     "p20_mount",
     "plate_type",
     "res_type",
     "filter_tip",
     "tip_reuse")

    # create labware
    source_plate = ctx.load_labware(plate_type, '7')
    # There could be a destination plate in slot 8 for cherry picking
    # Load something tall so the pipette doesn't hit it
    ctx.load_labware('usascientific_96_wellplate_2.4ml_deep', '8')
    reservoir = ctx.load_labware(res_type, '9')
    source = reservoir.wells()[0]
    if filter_tip:
        tips300 = ctx.load_labware('opentrons_96_filtertiprack_200ul', '10')
        tips20 = ctx.load_labware('opentrons_96_filtertiprack_20ul', '11')
    else:
        tips300 = ctx.load_labware('opentrons_96_tiprack_300ul', '10')
        tips20 = ctx.load_labware('opentrons_96_tiprack_20ul', '11')

    m300 = ctx.load_instrument('p300_multi_gen2', p300_mount)
    m20 = ctx.load_instrument('p20_multi_gen2', p20_mount)

    if not ctx.is_simulating():
        pick_up_current = 0.1  # 100 mA for single tip
        # Uncomment the next two lines if using Opentrons Robot Software version 7.1.x. # noqa:E501
        # Comment them if NOT using 7.1.x
        # for pipette in [m20, m300]:
        #     ctx._hw_manager.hardware.get_pipette(Mount.string_to_mount(pipette.mount)).update_config_item(  # noqa:E501
        #           {'pick_up_current': {8: pick_up_current}})

        # Uncomment the next two lines if using Opentrons Robot Software version 7.2.x # noqa:E501
        # Comment them if NOT using 7.2.x
        for pipette in [m20, m300]:
            ctx._hw_manager.hardware.get_pipette(Mount.string_to_mount(pipette.mount)).update_config_item(
                  {'pick_up_current': pick_up_current})

    tip300ctr = 95
    tip20ctr = 95

    def pick_up(pip):
        """`pick_up()` will pause the ctx when all tip boxes are out of
        tips, prompting the user to replace all tip racks. Once tipracks are
        reset, the ctx will start picking up tips from the first tip
        box as defined in the slot order when assigning the labware definition
        for that tip box. `pick_up()` will track tips for both pipettes if
        applicable.

        :param pipette: The pipette desired to pick up tip
        as definited earlier in the ctx (e.g. p300, m20).
        """
        nonlocal tip300ctr
        nonlocal tip20ctr

        if pip == m300:
            if tip300ctr < 0:
                ctx.home()
                ctx.pause('Please replace tips for P300 in slot 10.')
                tip300ctr = 95
            m300.pick_up_tip(tips300.wells()[tip300ctr])
            tip300ctr -= 1
        else:
            if tip20ctr < 0:
                ctx.home()
                ctx.pause('Please replace tips for P20 in slot 11.')
                tip20ctr = 95
            m20.pick_up_tip(tips20.wells()[tip20ctr])
            tip20ctr -= 1

    # create volumes list
    volumes = [float(cell) for cell in well_csv_to_list(volumes_csv)]

    is_warning = False

    for vol in volumes:
        if vol < 1:
            ctx.comment(
                'WARNING: volume {} is below pipette\'s minimum volume.'
                .format(vol))
            is_warning = True

    if is_warning:
        ctx.comment("\n")
        ctx.pause(
            "One or more minimum volume warnings were detected "
            "Do you wish to continue?\n")

    for i, vol in enumerate(volumes):
        pipette = m20 if vol <= 20 else m300
        if not pipette.has_tip:
            pick_up(pipette)
        if vol != 0:
            pipette.aspirate(vol, source)
            pipette.dispense(vol, source_plate.wells()[i])
        if tip_reuse == 'never':
            pipette.drop_tip()

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
    filename = f"detailed_action_json/6d901d.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)