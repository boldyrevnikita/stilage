from src.solution import State, ActionStatus
import src.pallet_packer.actions as actions


# GFS: General Failure State
class StateMachine:
    def __init__(self):
        self.states = {
            'S': State(lambda r, s: ActionStatus.SUCCESS, ['CBaU'], ['GFS']),
            'CBaU': State(actions.find_suitable_beams_and_upright,
                          ['RZC-90', 'CES-PHG'], ['GFS']),
            'RZC-90': State(actions.rotate_available_zone_90_clockwise,
                            ['CES-PHG'], ['GFS']),
            'RZCC-90': State(actions.rotate_available_zone_90_counterclockwise,
                             ['SNZ'], ['GFS']),
            'CES-PHG': State(
                actions.check_if_enough_space_for_horizontal_rack_placement,
                ['PHG'], ['SNZ']),
            'SNZ': State(actions.set_next_zone, ['CBaU'], ['SZZ-SNC']),
            'SZZ-SNC': State(actions.set_zone_to_zero_and_set_next_pallet,
                             ['CBaU'], ['TS']),
            'TS': State(lambda r, s: ActionStatus.SUCCESS, ['TS'], ['TS']),
            'PHG': State(actions.place_horizontal_rack_group,
                         ['CTNOZ-1'], ['GFS']),
        }
