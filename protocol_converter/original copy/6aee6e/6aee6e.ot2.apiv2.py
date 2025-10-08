import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6aee6e/6aee6e.ot2.apiv2.py"

metadata = {
    'apiLevel': '2.0',
    'protocolName': 'Ammonia ytrium dilution',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
}


def run(ctx):

    i_vol = get_values(  # noqa: F821
            'init_vol')[0]
    tip_racks = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_20ul',
            x) for x in [
            "7",
            "8"]]
    p20s = ctx.load_instrument(
        'p20_single_gen2',
        'right',
        tip_racks=tip_racks)
    ammonia = ctx.load_labware(
        "opentrons_6_tuberack_falcon_50ml_conical",
        '9').wells_by_name()["A1"]
    ytrium_plate = ctx.load_labware(
        "96wellplatemountedcappshaker_96_wellplate_360ul", '1')
    output_plate = ctx.load_labware("leo_99_wellplate_50ul", '3')

    def height_offset(vol_used, init_vol=i_vol):
        liquid_top = init_vol * 2
        # 1mm per 2ml
        if vol_used == 0:
            return liquid_top
        offset = vol_used / 2000
        if offset > liquid_top:
            ctx.comment("WARNING: Not enough liquid in 50ml tube")
            return 1
        return liquid_top - offset

    vol_used = 0

    for i, well in enumerate(ytrium_plate.wells()):
        output_well = output_plate.wells()[i]
        p20s.transfer(
            10,
            ammonia.bottom(
                height_offset(vol_used)),
            output_well,
            new_tip='always')
        vol_used += 10
        p20s.transfer(
            5, well, output_well, mix_after=(
                1, 10), new_tip='always')

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
    filename = f"detailed_action_json/6aee6e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)