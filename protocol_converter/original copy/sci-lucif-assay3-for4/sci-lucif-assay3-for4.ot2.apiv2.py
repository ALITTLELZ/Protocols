import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/sci-lucif-assay3-for4/sci-lucif-assay3-for4.ot2.apiv2.py"

# flake8: noqa

from opentrons.types import Point

metadata = {
    'protocolName': 'Luciferase Reporter Assay for NF-kB Activation (up to 4 plates) - Protocol 3: Treatment',
    'author': 'Boren Lin, Opentrons',
    'description': 'The protocol performs liquid handling to apply test articles (e.g., serial dilutions of drug candidates) to the reporter cells cultured in 96-well plates.',
    'apiLevel': '2.13'
}

PLATE_SLOT = [2, 5, 8, 11]
TOTAL_COL = 12

TREAT_PLATE_SLOT = [1, 4, 7, 10]

SUPERNATANT = 120
TREATMENT_VOL = 100

def run(ctx):

    [TOTAL_PLATE, m300_mount] = get_values(  # noqa: F821
        "TOTAL_PLATE", "m300_mount")

    # labware
    waste_res = ctx.load_labware('nest_1_reservoir_195ml', 9, 'waste')
    tiprack_refill = ctx.load_labware('opentrons_96_tiprack_300ul', 3)
    tips_refill_loc = tiprack_refill.rows()[0][:12]
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', 6)
    p300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=[tiprack])

    waste = waste_res.wells()[0]

    #protocol

    for x in range(TOTAL_PLATE):
        working_plate = ctx.load_labware('corning_96_wellplate_360ul_flat', PLATE_SLOT[x])
        treat_plate = ctx.load_labware('corning_96_wellplate_360ul_flat', TREAT_PLATE_SLOT[x])
        cells_all = working_plate.rows()[0][:TOTAL_COL]
        treatment = treat_plate.rows()[0][:TOTAL_COL]

        ctx.comment('\n\n\n~~~~~~~~REMOVE SUPERNATANT~~~~~~~~\n')

        p300.pick_up_tip()
        for i in range(TOTAL_COL):
            start = cells_all[i]
            p300.move_to(start.top(z=-0.2))
            p300.aspirate(SUPERNATANT*1.1, start.bottom(z=0.2).move(Point(x=-2.5)), rate = 0.2)
            p300.dispense(SUPERNATANT*1.1, waste.top(z=-5), rate = 3)
            p300.blow_out
        p300.drop_tip()

        ctx.comment('\n\n\n~~~~~~~~TREAT CELLS~~~~~~~~\n')

        ctx.pause('Place a New Full Tipbox on Slot 3')
        for j in range(TOTAL_COL):
            start = treatment[j]
            end = cells_all[j]
            p300.pick_up_tip(tips_refill_loc[j])
            p300.aspirate(TREATMENT_VOL, start.bottom(z=0.2), rate = 3)
            p300.air_gap(20)
            p300.dispense(TREATMENT_VOL+20, end.top(z=-4), rate = 0.3)
            p300.blow_out()
            p300.touch_tip()
            p300.drop_tip()

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
    filename = f"detailed_action_json/sci-lucif-assay3-for4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)