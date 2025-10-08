import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2942dd/2942dd.ot2.apiv2.py"

import csv
import math

metadata = {
    'title': 'Custom Transfer From CSV',
    'author': 'Steve Plonk',
    'apiLevel': '2.11'
}


def run(ctx):

    [vol_start_rnase, loc_rnase, vol_start_tween, loc_tween,
     count_mix, uploaded_csv] = get_values(  # noqa: F821
        "vol_start_rnase", "loc_rnase", "vol_start_tween", "loc_tween",
        "count_mix", "uploaded_csv")

    ctx.set_rail_lights(True)
    ctx.delay(seconds=10)

    # csv as list of dictionaries
    tfers = [line for line in csv.DictReader(uploaded_csv.splitlines()[3:])]

    # tips
    tips20 = [ctx.load_labware(
     'opentrons_96_filtertiprack_20ul', str(slot)) for slot in [5, 11]]
    tips300 = [ctx.load_labware(
     'opentrons_96_filtertiprack_200ul', str(slot)) for slot in [10]]

    # p300 single, p20 single
    p300s = ctx.load_instrument("p300_single_gen2", 'right', tip_racks=tips300)
    p20s = ctx.load_instrument("p20_single_gen2", 'left', tip_racks=tips20)

    # racks 1-4, fluidx rack, RNaseA, Tween 20
    racks = [ctx.load_labware(
     'opentrons_24_tuberack_2000ul', str(slot),
     'Rack {}'.format(str(index+1))) for index, slot in enumerate(
     [7, 4, 1, 8])]

    # to satisfy linter
    ctx.comment("Racks Loaded {}".format(racks))

    fluidxrack = ctx.load_labware(
     'fluidx_96_tuberack_1000ul', '9', 'Fluidx Rack')

    rnase = fluidxrack.wells_by_name()[loc_rnase]
    rnase.liq_vol = vol_start_rnase

    tween = fluidxrack.wells_by_name()[loc_tween]
    tween.liq_vol = vol_start_tween

    # return liquid height in a well
    def liq_height(well):
        if well.diameter is not None:
            radius = well.diameter / 2
            cse = math.pi*(radius**2)
        elif well.length is not None:
            cse = well.length*well.width
        else:
            cse = None
        if cse:
            return well.liq_vol / cse
        else:
            raise Exception("""Labware definition must
                supply well radius or well length and width.""")

    # workflow step 1: serum reagent to fluidx tube
    for tfer in tfers:
        if tfer['Quantity of Serum']:

            p300s.transfer(
             int(tfer['Quantity of Serum']),
             ctx.loaded_labwares[int(tfer['Deck Position'])].wells_by_name()[
              tfer['Rack Position']].bottom(1),
             fluidxrack.wells_by_name()[tfer['TubePosition Final']].bottom(1),
             new_tip='always')

    # workflow step 2: RNaseA to fluidx tube
    for tfer in tfers:
        if tfer['Quantity of EACH Sterilization Reagent']:

            v = float(tfer['Quantity of EACH Sterilization Reagent'])

            rnase.liq_vol -= v
            tipheight = liq_height(
             rnase) - 3 if liq_height(rnase) - 3 > 1 else 1

            p20s.transfer(
             v, rnase.bottom(tipheight),
             fluidxrack.wells_by_name()[tfer['TubePosition Final']].bottom(1),
             new_tip='always')

    # workflow step 3: Tween 20 to fluidx tube
    for tfer in tfers:
        if tfer['Quantity of EACH Sterilization Reagent']:

            v = float(tfer['Quantity of EACH Sterilization Reagent'])

            tween.liq_vol -= v
            tipheight = liq_height(
             tween) - 3 if liq_height(tween) - 3 > 1 else 1

            p20s.transfer(
             v, tween.bottom(tipheight),
             fluidxrack.wells_by_name()[tfer['TubePosition Final']].bottom(1),
             mix_after=(count_mix, 20), new_tip='always')

    # workflow step 4: count 30 minutes
    ctx.delay(minutes=30)

    ctx.comment("workflow steps 1-4 are complete")

    ctx.set_rail_lights(False)

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
    filename = f"detailed_action_json/2942dd.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)