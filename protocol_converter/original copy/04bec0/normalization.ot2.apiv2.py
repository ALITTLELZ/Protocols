import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/04bec0/normalization.ot2.apiv2.py"

metadata = {
    'protocolName': 'Normalization',
    'author': 'Trevor Ray <trevor.ray@opentrons.com>',
    'apiLevel': '2.14'
}


def run(ctx):

    input_csv, mount_p1000, mount_p300 = get_values(  # noqa: F821
        'input_csv', 'mount_p1000', 'mount_p300')

    sample_plate = ctx.load_labware('beckman_48_wellplate_1800ul', '7',
                                    'sample plate')
    sample_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
            slot, f'sample rack {i+1}')
        for i, slot in enumerate(['4', '1'])]
    normalization_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
            slot, f'normalization rack {i+1}')
        for i, slot in enumerate(['5', '2'])]
    final_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
            slot, f'final rack {i+1}')
        for i, slot in enumerate(['6', '3'])]
    tuberack50 = ctx.load_labware(
        'opentrons_6_tuberack_falcon_50ml_conical', '9', 'reagent tuberack')

    tiprack1000 = [
        ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot)
        for slot in ['8', '11']]
    tiprack200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '10')]

    p1000 = ctx.load_instrument(
        'p1000_single_gen2', mount_p1000, tip_racks=tiprack1000)
    p300 = ctx.load_instrument(
        'p300_single_gen2', mount_p300, tip_racks=tiprack200)

    sample_liquid = ctx.define_liquid(
        name="sample",
        description="sample",
        display_color="#FF0000",
    )
    water_liquid = ctx.define_liquid(
        name="water",
        description="water for normalization",
        display_color="#00FF00",
    )
    lds_liquid = ctx.define_liquid(
        name="LDS",
        description="2x LDS",
        display_color="#0000FF",
    )

    water = tuberack50.wells_by_name()['A1']
    lds = tuberack50.wells_by_name()['A2']

    def slow_withdraw(pip, well, delay=1.0):
        pip.default_speed = 25
        pip.move_to(well.top())
        if delay > 0:
            ctx.delay(seconds=delay)
        pip.default_speed = 400

    # parse
    biomass_data = [
        [float(val) for val in line.split(',')[1:]]
        for line in input_csv.splitlines()[1:]
        if line and line.split(',')[0].strip()
    ]
    biomass_data_flat = [val for row in biomass_data for val in row]
    mask = [1 if val > 0 else 0 for val in biomass_data_flat]

    # steps 1 - 2
    vol_sample = 800.0
    sources = [well for row in sample_plate.rows() for well in row]
    [s.load_liquid(sample_liquid, 800) for do, s in zip(mask, sources) if do]
    destinations = [
        well for rack in sample_racks for row in rack.rows() for well in row]
    p1000.flow_rate.aspirate = 100
    p1000.flow_rate.dispense = 1000
    for do, s, d in zip(mask, sources, destinations):
        if do:
            p1000.pick_up_tip()
            p1000.mix(10, 300, s.bottom(2))
            p1000.aspirate(vol_sample, s.bottom(2))
            p1000.air_gap(100)
            slow_withdraw(p1000, s)
            p1000.dispense(p1000.current_volume, d.bottom(10.5))
            p1000.blow_out(d.bottom(10.5))
            slow_withdraw(p1000, d)
            p1000.drop_tip()

    # steps 3-4
    target_conc = 54.0
    vol_sample_normalization = 100.0
    destinations = [
        well for rack in normalization_racks
        for row in rack.rows() for well in row]
    distribution_data = [
        [(biomass/target_conc - 1) * vol_sample_normalization, d]
        for do, biomass, d in zip(mask, biomass_data_flat, destinations)
        if do]
    vols_water = [d_data[0] for d_data in distribution_data]
    water.load_liquid(water_liquid, sum(vols_water))

    destinations_water = [d_data[1] for d_data in distribution_data]
    p1000.flow_rate.aspirate = 1000
    p1000.flow_rate.dispense = 1000
    p1000.pick_up_tip()
    p1000.distribute(
        vols_water, water.bottom(40),
        [d.bottom(5.5) for d in destinations_water], blow_out=True,
        disposal_volume=100, blowout_location='source well', new_tip='never')
    p1000.drop_tip()

    # steps 5-6
    sources = [
        well for rack in sample_racks for row in rack.rows() for well in row]
    destinations = [
        well for rack in normalization_racks for row in rack.rows()
        for well in row]
    p1000.flow_rate.aspirate = 300
    p1000.flow_rate.dispense = 300
    for do, s, d in zip(mask, sources, destinations):
        if do:
            p1000.pick_up_tip()
            p1000.aspirate(vol_sample_normalization, s.bottom(5.5))
            slow_withdraw(p1000, s)
            p1000.air_gap(20)
            p1000.dispense(20, d.top())
            p1000.dispense(vol_sample_normalization, d.bottom(5.5))
            p1000.mix(10, 100, d.bottom(5.5))
            p1000.blow_out(d.bottom(5.5))
            slow_withdraw(p1000, d)
            p1000.drop_tip()

    # steps 7-8
    vol_lds = 120.0
    lds.load_liquid(lds_liquid, sum(mask)*vol_lds)
    vol_disposal = 100.0
    destinations = [
        well for rack in normalization_racks for row in rack.rows()
        for well in row]
    p1000.flow_rate.aspirate = 500
    p1000.flow_rate.dispense = 500
    p1000.pick_up_tip()
    first = True
    for do, d in zip(mask, destinations):
        if do:
            if first:
                p1000.aspirate(vol_disposal, lds.bottom(50))
                first = False
            p1000.aspirate(vol_lds, lds.bottom(50))
            slow_withdraw(p1000, lds)
            p1000.air_gap(100)
            p1000.dispense(100, d.top())
            p1000.dispense(vol_lds, d.bottom(5.5))
    p1000.dispense(p1000.current_volume, lds.bottom(50))
    p1000.drop_tip()

    # steps 9-10
    vol_final = 40.0
    sources = [
        well for rack in normalization_racks for row in rack.rows()
        for well in row]
    destinations = [
        well for rack in final_racks for row in rack.rows()
        for well in row]
    p300.flow_rate.aspirate = 300
    p300.flow_rate.dispense = 300
    for do, s, d in zip(mask, sources, destinations):
        if do:
            p300.pick_up_tip()
            p300.mix(3, 100, s.bottom(5))
            p300.aspirate(vol_final, s.bottom(5))
            slow_withdraw(p300, s)
            p300.dispense(vol_final, d.bottom(5.5))
            p300.mix(10, 60, d.bottom(5.5))
            p300.blow_out(d.bottom(5.5))
            slow_withdraw(p300, d)
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
    filename = f"detailed_action_json/04bec0.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)