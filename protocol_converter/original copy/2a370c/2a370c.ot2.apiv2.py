import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2a370c/2a370c.ot2.apiv2.py"

from opentrons import protocol_api, types

metadata = {
    'protocolName': 'Omega Mag-Bind Bacterial DNA 96 Kit',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [samples, p300_mount, p1000_mount,
        engage_height] = get_values(  # noqa: F821
        "samples", "p300_mount", "p1000_mount", "engage_height")

    # Load Labware
    tipracks_200ul = [ctx.load_labware('opentrons_96_filtertiprack_200ul',
                                       slot) for slot in [4, 5]]
    tipracks_1000ul = [ctx.load_labware('opentrons_96_filtertiprack_1000ul',
                                        slot) for slot in [7, 8]]
    reservoir = ctx.load_labware('usascientific_12_reservoir_22ml', 2)
    ethanol_reservoir = ctx.load_labware('axygen_1_reservoir_90ml', 3)
    tuberack = ctx.load_labware(
                    'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', 6)
    mag_mod = ctx.load_module('magnetic module gen2', 1)
    mag_plate = mag_mod.load_labware('nest_96_wellplate_2ml_deep')
    trash = ctx.loaded_labwares[12]['A1']

    # Load Pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tipracks_200ul)
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=tipracks_1000ul)

    # Helper Functions
    def pick_up(pip, loc=None):
        try:
            if loc:
                pip.pick_up_tip(loc)
            else:
                pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            ctx.pause("Please replace the empty tip racks!")
            pip.reset_tipracks()
            pip.pick_up_tip()

    sides = [-1 + (((n // 8) % 2) * 1*2)
             for n in range(96)]

    def getWellSide(well, plate, custom_sides=None):
        index = plate.wells().index(well)
        if custom_sides:
            return custom_sides[index]
        return sides[index]

    def reset_flow_rates():
        p1000.flow_rate.aspirate = 274.7
        p1000.flow_rate.dispense = 274.7

    def remove_residual_supernatant(pip, vol):
        p1000.flow_rate.aspirate = 75
        p1000.flow_rate.dispense = 75
        for well in mag_plate_wells[:samples]:
            pick_up(pip)
            pip.aspirate(vol, well.bottom().move(types.Point(
                        x=getWellSide(well, mag_plate), y=0, z=0.5)))
            pip.dispense(vol, trash)
            pip.drop_tip()
        reset_flow_rates()

    # Volume Tracking
    class VolTracker:
        def __init__(self, labware, well_vol, pip_type='single',
                     mode='reagent', start=0, end=12, msg='Reset Labware'):
            try:
                self.labware_wells = dict.fromkeys(
                    labware.wells()[start:end], 0)
            except Exception:
                self.labware_wells = dict.fromkeys(
                    labware, 0)
            self.labware_wells_backup = self.labware_wells.copy()
            self.well_vol = well_vol
            self.pip_type = pip_type
            self.mode = mode
            self.start = start
            self.end = end
            self.msg = msg

        def tracker(self, vol):
            '''tracker() will track how much liquid
            was used up per well. If the volume of
            a given well is greater than self.well_vol
            it will remove it from the dictionary and iterate
            to the next well which will act as the reservoir.'''
            well = next(iter(self.labware_wells))
            if self.labware_wells[well] + vol >= self.well_vol:
                del self.labware_wells[well]
                if len(self.labware_wells) < 1:
                    ctx.pause(self.msg)
                    self.labware_wells = self.labware_wells_backup.copy()
                well = next(iter(self.labware_wells))
            if self.pip_type == 'multi':
                self.labware_wells[well] = self.labware_wells[well] + vol*8
            elif self.pip_type == 'single':
                self.labware_wells[well] = self.labware_wells[well] + vol
            if self.mode == 'waste':
                ctx.comment(f'''{well}: {int(self.labware_wells[well])} uL of
                            total waste''')
            else:
                ctx.comment(f'''{int(self.labware_wells[well])} uL of liquid
                            used from {well}''')
            return well

    # Wells
    mag_plate_wells = mag_plate.wells()[:samples]
    rnase = tuberack['A1']
    beads = tuberack['B1']
    ethanol = ethanol_reservoir['A1']
    msl = VolTracker(reservoir, 45000, 'single', start=0, end=4,
                     msg='Replenish MSL')
    spm = VolTracker(reservoir, 77000, 'single', start=6, end=12,
                     msg='Replenish SPM')

    # Protocol Steps

    # DNA Purification
    # Add 5 uL RNase A to Samples
    for well in mag_plate_wells:
        pick_up(p300)
        p300.aspirate(5, rnase)
        p300.dispense(5, well)
        p300.mix(20, 25)
        p300.drop_tip()

    # Delay at Room Temperature
    ctx.delay(minutes=5, msg="Incubating at Room Temperature for 5 minutes.")

    # Transfer 400 uL of MSL Buffer
    pick_up(p1000)
    for well in mag_plate_wells:
        p1000.transfer(400, msl.tracker(400), well.top(), new_tip='never')
    p1000.drop_tip()

    # Transfer 10 uL of Mag-Bind Particles
    for well in mag_plate_wells:
        pick_up(p300)
        p300.aspirate(10, beads)
        p300.dispense(10, well)
        p300.mix(20, 200)
        p300.drop_tip()

    # Transfer 528 uL of Ethnanol
    for well in mag_plate_wells:
        pick_up(p1000)
        p1000.aspirate(528, ethanol)
        p1000.dispense(528, well)
        p1000.mix(20, 500)
        p1000.drop_tip()

    # Delay at Room Temperature
    ctx.delay(minutes=5, msg="Incubating at Room Temperature for 5 minutes.")

    # Magnetic Separation
    mag_mod.engage(height=engage_height)
    ctx.delay(minutes=5, msg='Engaging Magnetic Module for 15 minutes.')

    # Remove Supernatant
    remove_residual_supernatant(p1000, 1000)

    for i in range(2):
        # Transfer 400 uL of SPM Buffer
        mag_mod.disengage()
        for well in mag_plate_wells:
            pick_up(p1000)
            p1000.aspirate(400, spm.tracker(400))
            p1000.dispense(400, well)
            p1000.mix(20, 200)
            p1000.drop_tip()

        # Incubation
        ctx.delay(minutes=3, msg="Incubate for 3 minutes at room temperature.")

        # Mix Mixture
        for well in mag_plate_wells:
            pick_up(p300)
            p300.mix(20, 200, well)
            p300.drop_tip()

        # Magnetic Separation
        mag_mod.engage(height=engage_height)
        ctx.delay(minutes=15, msg='Engaging Magnetic Module for 15 minutes.')

        # Remove Supernatant
        remove_residual_supernatant(p1000, 1000)

    # Air Dry
    ctx.delay(minutes=5, msg='Drying beads for 5 minutes.')

    # Remove Supernatant
    remove_residual_supernatant(p1000, 1000)

    # Air Dry
    ctx.delay(minutes=15, msg='Drying beads for 15 minutes.')

    mag_mod.disengage()
    ctx.comment('Protocol Complete!')

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
    filename = f"detailed_action_json/2a370c.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)