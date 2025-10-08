import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0b98cc/0b98cc.ot2.apiv2.py"

import math
from opentrons import protocol_api

metadata = {
    'protocolName': 'Viral Sample Titration',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [sample_cols, m300_type, m300_mount, media_trans_vol,
        sample_trans_vol, tip_strategy] = get_values(  # noqa: F821
        "sample_cols", "m300_type", "m300_mount", "media_trans_vol",
        "sample_trans_vol", "tip_strategy")

    # Load Labware
    analysis_dish = [ctx.load_labware('corning_96_wellplate_flat_bottom_360ul',
                                      slot, f'Analysis Dish {i}') for i, slot
                     in enumerate([2, 3, 5, 6], 1)]
    dilution_plate = [ctx.load_labware('corning_96_well_roundbottom_1ml', slot,
                                       f'Dilution Plate {i}') for i, slot
                      in enumerate([7, 10, 11, 8], 1)]
    media_reservoir = ctx.load_labware('nest_1_reservoir_195ml', 9,
                                       'Media Reservoir')['A1']
    tiprack = ctx.load_labware('opentrons_96_filtertiprack_200ul', 1)
    samples_plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt',
                                     4, 'Samples Plate')

    # Load Pipettes
    m300 = ctx.load_instrument(m300_type, m300_mount,
                               tip_racks=[tiprack])

    # Pickup and Track Tips
    def pick_up(pip):
        """Function that can be used instead of .pick_up_tip() that will pause
        robot when robot runs out of tips, prompting user to replace tips
        before resuming"""
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            ctx.pause("Replace the tips")
            pip.reset_tipracks()
            pip.pick_up_tip()

    # Populate Wells
    sample_wells = samples_plate.rows()[0][:sample_cols]
    dilution_dish_wells = [a for b in
                           zip(dilution_plate[0].rows()[0][:sample_cols],
                               dilution_plate[1].rows()[0],
                               dilution_plate[2].rows()[0],
                               dilution_plate[3].rows()[0]) for a in b]
    analysis_dish_wells = [column for dish in analysis_dish for i in range(3)
                           for column in dish.rows()[0][i::3]][:sample_cols*4]

    analysis_dish_final_cols = [analysis_dish[i]['A12'] for i in range(4)]

    '''Add Media to Dilution Plates'''

    # Get columns for addition of media based on sample columns number
    dilution_media_wells = [well for i in range(4) for well in
                            dilution_plate[i].rows()[0][:sample_cols]]
    # Transfer Media to Dilution Plates
    pick_up(m300)
    for well in dilution_media_wells:
        m300.flow_rate.dispense = 94
        # 200uL is the max volume for the filter tip rack
        num_trans = math.ceil(media_trans_vol/200)
        vol_per_trans = media_trans_vol/num_trans
        for _ in range(num_trans):
            m300.aspirate(vol_per_trans, media_reservoir.bottom(z=2))
            m300.dispense(vol_per_trans, well.bottom(z=10))
            m300.blow_out()

    ''' Dilute Samples and Transfer to Analysis Dish '''

    well_counter = 0
    dilution_counter = 0

    def dilution(disp_rate, message):
        nonlocal well_counter
        nonlocal dilution_counter
        if not m300.has_tip:
            pick_up(m300)
        m300.flow_rate.dispense = disp_rate
        # m300.mix(2, 100, dilution_dish_wells[well_counter].bottom(z=4))
        m300.aspirate(sample_trans_vol,
                      dilution_dish_wells[well_counter].bottom(z=4))
        # m300.air_gap(20)
        well_counter += 1
        m300.dispense(sample_trans_vol,
                      dilution_dish_wells[well_counter].bottom(z=4))
        # m300.touch_tip(v_offset=13)
        m300.flow_rate.dispense = 94
        m300.mix(5, 150, dilution_dish_wells[well_counter].bottom(z=5))
        # m300.touch_tip(v_offset=13)
        m300.flow_rate.dispense = 50
        m300.aspirate(50, dilution_dish_wells[well_counter].bottom(z=5))
        # m300.air_gap(20)
        m300.dispense(50, analysis_dish_wells[well_counter].bottom(z=3))
        m300.mix(1, 50, analysis_dish_wells[well_counter].bottom(z=3))
        # m300.touch_tip(v_offset=6.5)
        if tip_strategy == "dilution":
            # m300.air_gap(20)
            m300.drop_tip()
        dilution_counter += 1
        if tip_strategy == "sample":
            if dilution_counter == 3:
                m300.drop_tip()
                dilution_counter = 0
        ctx.comment(message)

    for sample in sample_wells:
        if not m300.has_tip:
            pick_up(m300)
        if well_counter != 0:
            well_counter += 1

        # Mix and transfer samples to dilution well
        m300.flow_rate.dispense = 94
        # m300.mix(2, 50, sample.bottom(z=4))
        m300.aspirate(sample_trans_vol, sample.bottom(z=3))
        # m300.air_gap(20)
        m300.dispense(sample_trans_vol,
                      dilution_dish_wells[well_counter].bottom(z=7))
        m300.blow_out()
        # m300.touch_tip(v_offset=13)
        ctx.comment("Undiluted Sample Transferred to First Dilution Block!")

        # Mix and transfer diluted sample (10^-1) to analysis dish (cells)
        m300.flow_rate.aspirate = 94
        m300.mix(5, 150, dilution_dish_wells[well_counter].bottom(z=5))
        m300.flow_rate.aspirate = 94
        m300.flow_rate.dispense = 50
        m300.aspirate(50, dilution_dish_wells[well_counter].bottom(z=5))
        # m300.air_gap(20)
        m300.dispense(50, analysis_dish_wells[well_counter].bottom(z=3))
        m300.mix(1, 50, analysis_dish_wells[well_counter].bottom(z=3))
        # m300.touch_tip(v_offset=6.5)
        # m300.air_gap(20)
        if tip_strategy == "dilution":
            m300.drop_tip()
        ctx.comment("First Dilution and Transfer Complete!")

        # Perform second dilution (10^-2) and transfer to analysis dish
        dilution(94, "Second Dilution and Transfer Complete!")

        # Perform third dilution (10^-3) and transfer to analysis dish
        dilution(94, "Third Dilution and Transfer Complete!")

        # Perform fourth dilution (10^-4) and transfer to analysis dish
        dilution(94, "Fourth Dilution and Transfer Complete!")

        # Check if Analysis Dish is complete and then prompt for removal
        if analysis_dish_wells[well_counter] in analysis_dish_final_cols:
            ctx.pause(f'''{analysis_dish_wells[well_counter]} is complete
                      please remove the plate.''')

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
    filename = f"detailed_action_json/0b98cc.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)