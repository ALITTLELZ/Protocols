import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/sci-lucif-assay4-for4/sci-lucif-assay4-for4.ot2.apiv2.py"

# flake8: noqa

from opentrons.types import Point

metadata = {
    'protocolName': 'Luciferase Reporter Assay for NF-kB Activation (up to 4 plates) - Protocol 4: Luciferase Activity Measurement',
    'author': 'Boren Lin, Opentrons',
    'description': 'The protocol performs liquid handling for reporter cell lysis and luciferase-catalyzed chemical reaction in 96-well plates, ready for bioluminescence measurement by a microplate reader.',
    'apiLevel': '2.13'
}

PLATE_SLOT = [2, 5, 8, 11]
TOTAL_COL = 12

SUPERNATANT =100
PBS_VOL = 100
LYSIS_VOL = 30
LUC_VOL = 100

def run(ctx):

    [TOTAL_PLATE, m300_mount] = get_values(  # noqa: F821
        "TOTAL_PLATE", "m300_mount")

    # labware
    reagent_stock = ctx.load_labware('nest_12_reservoir_15ml', 4, 'lysis buffer, luciferase reagent')
    PBS_stock = ctx.load_labware('nest_1_reservoir_195ml', 9, 'PBS')
    waste_res = ctx.load_labware('nest_1_reservoir_195ml', 6, 'waste')
    tips_refill = ctx.load_labware('opentrons_96_tiprack_300ul', 3)
    tips_refill_loc = tips_refill.wells()[:95]
    tips = ctx.load_labware('opentrons_96_tiprack_300ul', 1)
    p300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=[tips])

    pbs = PBS_stock.wells()[0]
    lysis = reagent_stock.wells()[0]
    luciferase = reagent_stock.wells()[6:6+TOTAL_PLATE]
    waste = waste_res.wells()[0]

    #protocol

    for x in range(TOTAL_PLATE):
        ctx.pause('Place a New Full Tipbox on Slot 3')

        working_plate = ctx.load_labware('corning_96_wellplate_360ul_flat', PLATE_SLOT[x])
        cells_all = working_plate.rows()[0][:TOTAL_COL]

        ctx.comment('\n\n\n~~~~~~~~REMOVE SUPERNATANT and WASH~~~~~~~~\n')
        for i in range(TOTAL_COL):
            tip_loc = int(i*8)
            p300.pick_up_tip(tips_refill_loc[tip_loc])
            start = cells_all[i]
            end = waste
            p300.move_to(start.top(z=-0.2))
            p300.aspirate(SUPERNATANT*1.2, start.bottom(z=0.2).move(Point(x=-2.5)), rate = 0.2)
            p300.air_gap(20)
            p300.dispense(SUPERNATANT*1.2+20, end.top(z=-5), rate = 3)
            p300.blow_out
            p300.return_tip()

        p300.pick_up_tip()
        for j in range(TOTAL_COL):
            start = pbs
            end = cells_all[j]
            p300.aspirate(PBS_VOL, start.bottom(z=0.5), rate = 3)
            p300.air_gap(20)
            p300.dispense(PBS_VOL+20, end.top(z=-2), rate = 0.3)
            p300.blow_out()
            p300.touch_tip()
        p300.drop_tip()

        for k in range(TOTAL_COL):
            tip_loc = int(k*8)
            p300.pick_up_tip(tips_refill_loc[tip_loc])
            start = cells_all[k]
            end = waste
            p300.move_to(start.top(z=-0.2))
            p300.aspirate(PBS_VOL*1.2, start.bottom(z=0.2).move(Point(x=-2.5)), rate = 0.2)
            p300.air_gap(20)
            p300.dispense(PBS_VOL*1.2+20, end.top(z=-5), rate = 3)
            p300.blow_out
            p300.drop_tip()

        ctx.comment('\n\n\n~~~~~~~~ADD LYSIS BUFFER~~~~~~~~\n')
        p300.pick_up_tip()
        for l in range(TOTAL_COL):
            start = lysis
            end = cells_all[l]
            p300.aspirate(LYSIS_VOL, start.bottom(z=0.5), rate = 0.5)
            ctx.delay(seconds=2)
            p300.air_gap(20)
            p300.dispense(LYSIS_VOL+20, end.bottom(z=5), rate = 0.3)
            ctx.delay(seconds=2)
            p300.touch_tip()
        p300.drop_tip()

        ctx.delay(minutes=5)

        ctx.comment('\n\n\n~~~~~~~~ADD LUCIFERASE ASSAY REAGENT~~~~~~~~\n')
        p300.pick_up_tip()
        for m in range(TOTAL_COL):
            start = luciferase[x]
            end = cells_all[m]
            p300.aspirate(LUC_VOL, start.bottom(z=0.5), rate = 0.75)
            ctx.delay(seconds=2)
            p300.air_gap(20)
            p300.dispense(LUC_VOL+20, end.top(z=-0.5), rate = 0.75)
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
    filename = f"detailed_action_json/sci-lucif-assay4-for4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)