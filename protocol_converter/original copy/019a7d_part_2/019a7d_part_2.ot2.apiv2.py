import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/019a7d_part_2/019a7d_part_2.ot2.apiv2.py"

"""PROTOCOL."""
import math
metadata = {
    'protocolName': 'Nucleic Acid Purification/Cloning',
    'author': 'Opentrons',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'   # CHECK IF YOUR API LEVEL HERE IS UP TO DATE
                         # IN SECTION 5.2 OF THE APIV2 "VERSIONING"
}


def run(ctx):
    """PROTOCOL BODY."""
    [num_samples, omni_tray_24, omni_tray_96, heat_shock, agar_volume, dwp,
     dwp_volume
     ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "num_samples", "omni_tray_24", "omni_tray_96", "heat_shock",
        "agar_volume", "dwp", "dwp_volume")

    # number of samples
    num_cols = math.ceil(num_samples/8)

    # load modules
    temp_1 = ctx.load_module('tempdeck', '1')
    temp_3 = ctx.load_module('tempdeck', '3')

    # load labware
    mix_n_go = temp_1.load_labware('azentalifesciences_96_aluminumblock_200ul')
    assemb_plate = temp_3.load_labware('azentalifesciences_96_aluminumblock'
                                       '_200ul')
    dwp_plate = ctx.load_labware('greiner_96_wellplate_2000ul', "11")

    dwp_dest_list = dwp_plate.rows()[0][:num_cols]
    samples_source_s = mix_n_go.wells()[:num_samples]
    samples_source_m = mix_n_go.rows()[0][:num_cols]
    assemb_liquid_m = assemb_plate.rows()[0][:num_cols]

    # load tipracks
    tiprack = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
               for slot in ['4', '10']]
    # load instrument
    p20 = ctx.load_instrument(
                        'p20_single_gen2',
                        mount='right',
                        tip_racks=tiprack
    )
    m20 = ctx.load_instrument(
                        'p20_multi_gen2',
                        mount='left',
                        tip_racks=tiprack
    )

    # load labware

    agar_plates_24 = [ctx.load_labware('customagar_24_wellplate_200ul', slot)
                      for slot in ['5', '6', '7', '8']]
    agar_locations_24 = [well for plate in agar_plates_24
                         for well in plate.wells()[:num_samples]]
    tip_recycle_24 = tiprack[0].wells()[0:num_samples]
    agar_plate_96 = [ctx.load_labware('customagar_96_wellplate_200ul', slot)
                     for slot in ['9']]
    agar_locations_96 = [well for plate in agar_plate_96
                         for well in plate.rows()[0][:num_cols]]
    samples_source_m = mix_n_go.rows()[0][:num_cols]
    tip_recycle_96 = tiprack[0].rows()[0][0:num_cols]

    # PROTOCOL
    temp_1.set_temperature(4)
    for source, dests in zip(assemb_liquid_m, samples_source_m):
        m20.transfer(5,
                     source,
                     dests,
                     new_tip='always',
                     mix_after=(3, 5),
                     blow_out=True,
                     blowout_location='destination well',
                     trash=False)

    # temp module to 42 celsius for 40s then back to 4 celsisus
    if heat_shock:
        temp_1.set_temperature(42)
        ctx.delay(seconds=40)
        temp_1.set_temperature(4)

    # Agar 24 Plate Transfer
    if omni_tray_24:
        for tips, source, dest in zip(tip_recycle_24, samples_source_s,
                                      agar_locations_24):
            p20.pick_up_tip(tips)
            p20.aspirate(agar_volume, source)
            p20.dispense(agar_volume, dest.top(5))
            p20.return_tip()
    # Agar 96 Plate Transfer
    if omni_tray_96:
        for tips, source, dest in zip(tip_recycle_96, samples_source_m,
                                      agar_locations_96):
            m20.pick_up_tip(tips)
            m20.aspirate(agar_volume, source)
            m20.dispense(agar_volume, dest.top(5))
            m20.return_tip()

    # DWP/LC Addition If Needed
    if dwp:
        for tips, source, dest in zip(tip_recycle_96, samples_source_m,
                                      dwp_dest_list):
            m20.pick_up_tip(tips)
            m20.aspirate(dwp_volume, source)
            m20.dispense(dwp_volume, dest.bottom(10))
            m20.mix(10, 20, dest)
            m20.blow_out(dest.top(-1))
            m20.drop_tip()
    for c in ctx.commands():
        print(c)

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
    filename = f"detailed_action_json/019a7d_part_2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)