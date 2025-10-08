import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7aa3fd-library-quantification/lib_quant.ot2.apiv2.py"

# metadata
metadata = {
    'protocolName': 'NGS Prep Part 2/3: Library Quantification',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    [p10_mount, p300_mount] = get_values(  # noqa: F821
        "p10_mount", "p300_mount")

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
    tempdeck.set_temperature(4)
    qpcr_plate = tempdeck.load_labware(
        'eppendorftwin.tec_96_wellplate_150ul')
    dna_plate = ctx.load_labware(
        'eppendorftwin.tec_96_wellplate_150ul', '5', 'DNA plate')
    tiprack200 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', '6', '200ul filter tiprack')]
    elution_plate = ctx.load_labware(
        'eppendorftwin.tec_96_wellplate_150ul', '9', 'elution plate')

    # pipettes
    p10 = ctx.load_instrument(
        'p10_single', mount=p10_mount, tip_racks=tiprack10)
    p300 = ctx.load_instrument(
        'p300_single', mount=p300_mount, tip_racks=tiprack200)

    # reagent setup
    water = tuberack.rows()[0][:5]
    qpcr_mm = tuberack.rows()[1][0]

    # transfer SPRI elution plate to DNA plate
    for s, d in zip(elution_plate.rows()[0], dna_plate.rows()[1]):
        p10.pick_up_tip()
        p10.aspirate(7, s.top())
        p10.aspirate(2, s)
        p10.air_gap(1)
        p10.dispense(10, d.bottom(2))
        p10.blow_out(d.bottom(2))
        p10.touch_tip(d, v_offset=-5)
        p10.drop_tip()

    # sample dilution 1
    for d in dna_plate.rows()[1]:
        p10.pick_up_tip()
        p10.transfer(18, water[0], d.top(-2), new_tip='never')
        p10.mix(3, 9, d)
        p10.blow_out(d.top(-2))
        p10.drop_tip()

    # transfer water to specified wells of dilution plate
    p300.pick_up_tip()
    for s, d in zip(water, dna_plate.rows()[2:7]):
        p300.distribute(
            90,
            s,
            d,
            air_gap=10,
            disposal_volume=0,
            blow_out=True,
            new_tip='never'
        )
    p300.drop_tip()

    # sample serial dilution
    for s_row, d_row in zip(dna_plate.rows()[1:6], dna_plate.rows()[2:7]):
        for s, d in zip(s_row, d_row):
            p10.transfer(10, s, d, blow_out=True)
        for d in d_row:
            p300.pick_up_tip()
            p300.mix(5, 90, d)
            p300.blow_out(d.top(-2))
            p300.drop_tip()

    ctx.pause('Replace 10 µL tip rack and insert QPCR mastermix into position  B1 of reagent rack.')
    p10.reset_tipracks()

    # QPCR plate setup
    mm_wells = [well for row in qpcr_plate.rows() for well in row]
    for _ in range(3):
        mm_wells.pop(0)
    p300.transfer(
        16, qpcr_mm, [well for well in mm_wells], air_gap=0, blow_out=True)

    srcs1 = [well for well in dna_plate.rows()[0][:7]]
    srcs2 = [
        well for row in ['F', 'G']
        for well in dna_plate.rows_by_name()[row]
    ]
    srcs = srcs1 + srcs2

    dest_sets1 = [
        [well for row in qpcr_plate.rows()[:2] for well in row][i*3:(i+1)*3]
        for i in range(7)
    ]
    dest_sets2 = [
        col[i:i+3] for i in [2, 5]
        for col in qpcr_plate.columns()
    ]
    dest_sets = dest_sets1 + dest_sets2

    for s, dest_set in zip(srcs, dest_sets):
        p10.transfer(
            4, s, dest_set, mix_after=(3, 5), blow_out=True, new_tip='always')

    ctx.comment('Seal QPCR plate and load onto the thermocycler.')

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
    filename = f"detailed_action_json/7aa3fd-library-quantification.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)