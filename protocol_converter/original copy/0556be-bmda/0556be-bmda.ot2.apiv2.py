import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0556be-bmda/0556be-bmda.ot2.apiv2.py"

metadata = {
    'protocolName': 'BMDA - Dengue Protocol',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [p300_mount, temperature, final_tubes, comp_asp_speed, comp_disp_speed,
        comp1_vol, comp2_vol, comp3_vol, comp4_vol, comp5_vol, comp6_vol,
        comp7_vol, comp8_vol, comp9_vol, comp10_vol, comp11_vol,
        comp12_vol, mm_vol, mix_reps, mix_vol, asp_delay,
        disp_delay, air_gap_vol] = get_values(  # noqa: F821
        "p300_mount", "temperature", "final_tubes", "comp_asp_speed",
        "comp_disp_speed", "comp1_vol", "comp2_vol", "comp3_vol",
        "comp4_vol", "comp5_vol", "comp6_vol", "comp7_vol", "comp8_vol",
        "comp9_vol", "comp10_vol", "comp11_vol", "comp12_vol", "mm_vol",
        "mix_reps", "mix_vol", "asp_delay", "disp_delay", "air_gap_vol")

    # Load Labware
    temp_mod = ctx.load_module('temperature module gen2', 10)
    reagents = temp_mod.load_labware(
        'opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    pcr_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', 8)
    tiprack_200ul = ctx.load_labware('opentrons_96_filtertiprack_200ul', 1)

    # Load Instruments
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=[tiprack_200ul])

    # Get Sample Wells
    mm = reagents.wells()[0]
    components = reagents.wells()[12:]
    volumes = [int(vol) for vol in [comp1_vol, comp2_vol, comp3_vol, comp4_vol,
                                    comp5_vol, comp6_vol, comp7_vol, comp8_vol,
                                    comp9_vol, comp10_vol, comp11_vol,
                                    comp12_vol]]
    final_tubes = int(final_tubes)
    mm_vol = float(mm_vol)

    # Set Temperature to 8C
    temp_mod.set_temperature(temperature)

    # Add Components to Master Mix
    p300.flow_rate.aspirate = comp_asp_speed
    p300.flow_rate.dispense = comp_disp_speed
    for vol, source in zip(volumes, components):
        p300.pick_up_tip()
        p300.aspirate(air_gap_vol, source.top())
        p300.aspirate(vol, source)
        ctx.delay(seconds=asp_delay)
        p300.air_gap(air_gap_vol)
        p300.dispense(vol+air_gap_vol*2, mm)
        ctx.delay(seconds=disp_delay)
        p300.drop_tip()
    p300.pick_up_tip()
    p300.mix(mix_reps, mix_vol, mm)
    p300.drop_tip()

    # Reset Flow Rates
    p300.flow_rate.aspirate = 92.86
    p300.flow_rate.dispense = 92.86

    # Get well distribution for PCR plate
    pcr_plate_wells = [pcr_plate.columns()[i] for i in [0, 3, 6, 9]]
    pcr_plate_wells = [wells for well in pcr_plate_wells
                       for wells in well][:final_tubes]

    # Add Master Mix to 32 wells
    p300.pick_up_tip()
    for dest in pcr_plate_wells:
        p300.aspirate(air_gap_vol, mm.top())
        p300.aspirate(mm_vol, mm)
        ctx.delay(seconds=asp_delay)
        p300.air_gap(air_gap_vol)
        p300.touch_tip()
        p300.dispense(mm_vol+air_gap_vol*2, dest)
        p300.touch_tip()
        ctx.delay(seconds=disp_delay)
    p300.drop_tip()

    # Deactivate Temp Mod
    temp_mod.deactivate()

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
    filename = f"detailed_action_json/0556be-bmda.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)