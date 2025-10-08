import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/01a6b9/media_filling.ot2.apiv2.py"

import math
from opentrons import protocol_api

metadata = {
    'protocolName': 'Media Refilling',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'apiLevel': '2.13'
}

offset_aspiration_from_bottom = 0.5


def run(ctx):

    [vol_refill, num_lw, do_remove_media, do_premix, lw_refill, lw_media,
     height_offset_aspirate, height_offset_dispense, type_pip,
     mount_pip] = get_values(  # noqa:F821
     'vol_refill', 'num_lw', 'do_remove_media', 'do_premix',
     'lw_refill', 'lw_media', 'height_offset_aspirate',
     'height_offset_dispense', 'type_pip', 'mount_pip')

    tip_vol_map = {
        20: '20',
        300: '200',
        1000: '1000'
    }

    pipette = ctx.load_instrument(type_pip, mount_pip)
    tiprack_type = f'opentrons_96_filtertiprack_ {tip_vol_map[int(pipette.max_volume)]}ul'

    plates = [
        ctx.load_labware(lw_refill, slot)
        for slot in range(1, 1+num_lw)]
    media_res = ctx.load_labware(lw_media, '10', 'media reservoir (A1)')
    if len(media_res.wells()) > 1:
        media = media_res.wells()[:num_lw]
    else:
        media = [media_res.wells()[0]]*num_lw
    waste = ctx.load_labware(
        lw_media, '11', 'waste reservoir').wells()[0].top()

    grid_size = len(plates[0].rows()) * len(plates[0].columns())
    if grid_size < 96 and pipette.channels == 8:
        raise Exception('Incompatible labware with 8-channel pipette.')

    tipracks = [
        ctx.load_labware(tiprack_type, slot)
        for slot in range(num_lw+1, 10)]
    pipette.tip_racks = tipracks
    if pipette.channels == 8:
        pipette.starting_tip = pipette.tip_racks[0].rows()[0][1]
    else:
        pipette.starting_tip = pipette.tip_racks[0].wells()[1]
    media_tip = pipette.tip_racks[0].wells()[0]

    def slow_withdraw(well, delay_seconds=2.0, pip=pipette):
        pip.default_speed /= 16
        if delay_seconds > 0:
            ctx.delay(seconds=delay_seconds)
        pip.move_to(well.top())
        pip.default_speed *= 16

    def pick_up(pip=pipette):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause("Replace all tipracks")
            pip.reset_tipracks()
            if pip.channels == 8:
                pipette.starting_tip = pip.tip_racks[0].rows()[0][1]
            else:
                pipette.starting_tip = pip.tip_racks[0].wells()[1]
            pip.pick_up_tip()

    if pipette.channels == 8:
        if grid_size == 96:
            plate_locs_sets = [plate.rows()[0] for plate in plates]
        else:
            plate_locs_sets = [
                [well for row in plate.rows()[:2] for well in row]
                for plate in plates]
    else:
        plate_locs_sets = [plate.wells() for plate in plates]

    num_trans = math.ceil(
        vol_refill/pipette.tip_racks[0].wells()[0].max_volume)
    vol_per_trans = round(vol_refill/num_trans, 1)

    if not do_remove_media:
        pipette.pick_up_tip(media_tip)

    num_total_locs = len(plates)*len(plates[0].wells())

    for p, loc_set in enumerate(plate_locs_sets):

        media_source = media[p]

        for i, well in enumerate(loc_set):

            # remove old volume
            if do_remove_media:
                pick_up()
                for _ in range(num_trans):
                    pipette.aspirate(
                        vol_per_trans, well.bottom(height_offset_aspirate))
                    slow_withdraw(well)
                    pipette.dispense(vol_per_trans, waste)
                pipette.drop_tip()

            # add media
            if not pipette.has_tip:
                pipette.pick_up_tip(media_tip)
            if do_premix:
                pipette.mix(5, pipette.tip_racks[0].wells()[0].max_volume*0.8,
                            media_source.bottom(2))
            for _ in range(num_trans):
                pipette.aspirate(vol_per_trans, media_source.bottom(2))
                slow_withdraw(media_source)
                pipette.dispense(vol_per_trans,
                                 well.top(height_offset_dispense))
                slow_withdraw(well)

            well_ind = p*len(plates[0].wells()) + i
            if do_remove_media:
                if well_ind == num_total_locs - 1:
                    pipette.drop_tip()
                else:
                    pipette.return_tip()

    if pipette.has_tip:
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
    filename = f"detailed_action_json/01a6b9.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)