import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7aa3fd-size-selection/size_selection.ot2.apiv2.py"

from opentrons import types
import math

# metadata
metadata = {
    'protocolName': 'NGS Prep Part 1/3: Size Selection',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    [num_samples, bead_mix_vol, bead_mix_speed,
        bead_mix_reps, p10_mount, p300_mount] = get_values(  # noqa: F821
            "num_samples", "bead_mix_vol", "bead_mix_speed", "bead_mix_reps",
            "p10_mount", "p300_mount"
        )
    num_samples = int(num_samples)

    # load modules and labware
    magdeck = ctx.load_module('magdeck', '1')
    mag_plate = magdeck.load_labware(
        'eppendorftwin.tec_96_wellplate_150ul')
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
        '2',
        '2ml reagent rack'
    )
    tiprack10 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_10ul', '3', '10ul filter tips')]
    tipracks200 = [
        ctx.load_labware(
            'opentrons_96_filtertiprack_200ul', slot, '200ul filter tips')
        for slot in ['5', '6']]
    elution_plate = ctx.load_labware(
        'eppendorftwin.tec_96_wellplate_150ul', '9', 'elution plate')

    # pipettes
    p10 = ctx.load_instrument(
        'p10_single', mount=p10_mount, tip_racks=tiprack10)
    p300 = ctx.load_instrument(
        'p300_single', mount=p300_mount, tip_racks=tipracks200)

    # reagent setup
    beads = tuberack.rows()[0][0]
    etoh = tuberack.rows()[1][:3]
    edta = tuberack.rows()[2][0]

    # samples
    mag_samples, elution_samples = [
        [well for row in plate.rows()[:math.ceil(int(num_samples)/12)]
         for well in row]
        for plate in [mag_plate, elution_plate]
    ]

    # selective DNA binding to SPRI beads
    p300.flow_rate.aspirate = bead_mix_speed
    p300.flow_rate.dispense = bead_mix_speed
    p300.pick_up_tip()
    for _ in range(bead_mix_reps):
        p300.aspirate(bead_mix_vol, beads.bottom(4))
        p300.dispense(bead_mix_vol, beads.bottom(15))
    p300.blow_out(beads.top(-5))
    p300.flow_rate.aspirate = 150
    p300.flow_rate.dispense = 300
    for m in mag_samples:
        if not p300.hw_pipette['has_tip']:
            p300.pick_up_tip()
        p300.transfer(40, beads.bottom(3), m.bottom(2), new_tip='never')
        p300.mix(3, 30, m.bottom(2))
        p300.blow_out(m.top(-2))
        p300.drop_tip()

    # supernatant removal
    magdeck.engage(height=18)
    ctx.comment('Incubating on magnet for 2 minutes')
    ctx.delay(minutes=2)
    for m in mag_samples:
        p300.transfer(
            180,
            m.bottom(0.5),
            p300.trash_container.wells()[0].top(),
            air_gap=20
        )

    # ethanol washes
    for _ in range(2):
        for i, m in enumerate(mag_samples):
            etoh_tube = etoh[(i % 12)//4]
            p300.pick_up_tip()
            p300.transfer(
                180,
                etoh_tube.bottom(3),
                m.bottom(2),
                air_gap=20,
                new_tip='never'
            )
            p300.blow_out(m.top(-2))
            p300.drop_tip()
        ctx.comment('Incubating for 30 seconds')
        ctx.delay(seconds=30)
        for m in mag_samples:
            p300.transfer(
                180,
                m.bottom(0.5),
                p300.trash_container.wells()[0].top(),
                air_gap=20
            )

    ctx.comment('Incubating for 2 minutes')
    ctx.delay(minutes=2)
    for m in mag_samples:
        p300.transfer(
            180,
            m.bottom(0.5),
            p300.trash_container.wells()[0].top(),
            air_gap=20
        )

    # DNA elution
    magdeck.disengage()
    for i, m in enumerate(mag_samples):
        angle = 1 if i % 2 == 0 else -1
        disp_loc = m.center().move(types.Point(x=2.9*angle, y=-0, z=-6.5))
        p10.pick_up_tip()
        p10.aspirate(10, edta.bottom(2))
        p10.move_to(m.bottom(2))
        p10.dispense(10, disp_loc)
        p10.mix(10, 8, m)
        p10.drop_tip()

    # DNA transfer to elution plate
    magdeck.engage(height=18)
    ctx.comment('Incubating on magnet for 2 minutes.')
    for i, (m, e) in enumerate(zip(mag_samples, elution_samples)):
        angle = -1 if i % 2 == 0 else 1
        asp_loc = m.center().move(types.Point(x=2*angle, y=0, z=-6.5))
        p10.pick_up_tip()
        p10.transfer(10, asp_loc, e, new_tip='never')
        p10.blow_out(e)
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
    filename = f"detailed_action_json/7aa3fd-size-selection.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)