import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1185d3/1185d3.ot2.apiv2.py"

metadata = {
    'apiLevel': '2.5',
    'protocolName': 'MagMAX Viral/Pathogen Nucleic Acid Isolation Kit wash',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request'
}


def run(ctx):
    magdeck = ctx.load_module('magnetic module gen2', '4')
    magdeck.disengage()
    mag_plate = magdeck.load_labware('nest_96_wellplate_2ml_deep',
                                     'deepwell plate')

    elution_plate = ctx.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt', '3')
    wash_buffer = ctx.load_labware(
        'nest_1_reservoir_195ml', '5').wells()[0]
    ethanol_80 = ctx.load_labware(
        'nest_1_reservoir_195ml', '1').wells()[0]
    liquid_trash = ctx.load_labware(
        'nest_1_reservoir_195ml', '2').wells()[0]

    tip_racks = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul',
            x) for x in [
            '6',
            '9',
            '8',
            '7',
            '10',
            '11'
        ]]
    p300m = ctx.load_instrument(
        'p300_multi_gen2', "right", tip_racks=tip_racks)

    magdeck.engage()
    ctx.delay(600)

    mag_cols = mag_plate.rows()[0]
    for col in mag_cols:
        p300m.pick_up_tip()
        p300m.transfer(480, col, liquid_trash.top(), new_tip='never')
        p300m.drop_tip()

    magdeck.disengage()

    for col in mag_cols:
        p300m.pick_up_tip()
        [p300m.transfer(200, wash_buffer, col.top(), new_tip='never')
         for _ in [1, 2]]
        p300m.transfer(
            100,
            wash_buffer,
            col,
            new_tip='never',
            mix_after=(
                5,
                100))
        p300m.drop_tip()

    magdeck.engage()
    ctx.delay(120)

    for col in mag_cols:
        p300m.pick_up_tip()
        p300m.transfer(500, col, liquid_trash.top(), new_tip='never')
        p300m.drop_tip()

    magdeck.disengage()

    for col in mag_cols:
        p300m.pick_up_tip()
        [p300m.transfer(200, ethanol_80, col.top(), new_tip='never')
         for _ in [1, 2]]
        p300m.transfer(
            100,
            ethanol_80,
            col,
            new_tip='never',
            mix_after=(
                5,
                100))
        p300m.drop_tip()

    magdeck.engage()
    ctx.delay(120)

    for col in mag_cols:
        p300m.pick_up_tip()
        p300m.transfer(500, col, liquid_trash.top(), new_tip='never')
        p300m.drop_tip()

    magdeck.disengage()

    for col in mag_cols:
        p300m.pick_up_tip()
        p300m.transfer(125, ethanol_80, col.top(), new_tip='never')
        p300m.transfer(
            125,
            ethanol_80,
            col,
            new_tip='never',
            mix_after=(
                5,
                100))
        p300m.drop_tip()

    magdeck.engage()
    ctx.pause("""Drain liquid from liquid trash.
            Replace tip racks in deck slots 6, 9, and 8.
            Replace ethanol in deck slot 1
            with a trough of elution solution""")
    p300m.reset_tipracks()
    ctx.delay(120)

    for col in mag_cols:
        p300m.pick_up_tip()
        p300m.transfer(300, col, liquid_trash.top(), new_tip='never')
        p300m.drop_tip()

    magdeck.disengage()

    ctx.delay(300)

    [p300m.transfer(50, ethanol_80, col, mix_after=(10, 40))
     for col in mag_cols]

    ctx.pause(
        """Place into 65c incubator for 10 minutes,
        then return plate to magnetic module""")

    magdeck.engage()
    ctx.delay(180)
    for i, col in enumerate(mag_cols):
        p300m.transfer(50, col, elution_plate.rows()[0][i])

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
    filename = f"detailed_action_json/1185d3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)