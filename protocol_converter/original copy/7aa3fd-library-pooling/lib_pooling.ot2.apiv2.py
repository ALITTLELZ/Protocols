import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7aa3fd-library-pooling/lib_pooling.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'NGS Prep Part 3/3: Library Pooling',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    [input_csv, vol_water, p10_mount, p300_mount] = get_values(  # noqa: F821
        "input_csv", "vol_water", "p10_mount", "p300_mount")

    # load modules and labware
    ctx.load_module('magdeck', '1')
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
        '2',
        '2ml reagent rack'
    )
    tiprack10 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_10ul', '3', '10ul filter tips')]
    tempdeck = ctx.load_module('tempdeck', '4')
    tubeblock = tempdeck.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_snapcap'
    )
    tempdeck.set_temperature(4)
    tiprack200 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', '6', '200ul filter tips')]
    elution_plate = ctx.load_labware(
        'eppendorftwin.tec_96_wellplate_150ul', '9', 'elution plate')

    # pipettes
    p10 = ctx.load_instrument(
        'p10_single', mount=p10_mount, tip_racks=tiprack10)
    p300 = ctx.load_instrument(
        'p300_single', mount=p300_mount, tip_racks=tiprack200)

    # reagent setup
    water = tuberack.wells()[0]
    pool = tubeblock.wells()[0]

    # parse
    t_data = [
        [elution_plate.wells_by_name()[
            t.split(',')[0].strip().upper()], float(t.split(',')[1])]
        for t in input_csv.splitlines()[1:]
    ]

    # pre-transfer water
    p300.transfer(vol_water, water, pool.bottom(5), blow_out=True)

    # transer .csv-specified volume of sample to the pooling tube
    for trans in t_data:
        vol, src = [trans[1], trans[0]]
        v_asp = 10 - vol if 10 - vol < 10 else 0
        p10.pick_up_tip()
        p10.aspirate(vol, src)
        p10.touch_tip(src)
        p10.aspirate(v_asp, pool.bottom(2))
        p10.dispense(10, pool.bottom(2))
        p10.blow_out(pool.bottom(5))
        p10.drop_tip()

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
    filename = f"detailed_action_json/7aa3fd-library-pooling.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)