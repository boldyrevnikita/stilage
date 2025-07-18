from copy import deepcopy
from enum import Enum

import src.pallet_packer.actions as actions
from src.pallet_packer.solution import (ActionFailure, ActionStatus, Solution,
                                        State)

# from src.visualize import visualize_solution_decorator


class Block(Enum):
    MAIN = 1
    RACK_PLACEMENT = 2
    GOOZ = 3
    JOOZ = 4
    DSFX = 5
    EOZ = 6
    CF = 7
    MSR = 8


def get_general_states() -> dict[str, State]:
    return {
        'GFS': State(actions.default_action, ['GFS'], ['GFS']),
        'TS-DEL': State(actions.default_action,
                        ['TS-DEL'], ['TS-DEL']),
        'TS': State(actions.default_action, ['TS'], ['TS'])
    }


def get_main_loop_states() -> dict[str, State]:
    return {
        f'{Block.MAIN}-S': State(
            actions.default_action,
            [f'{Block.MAIN}-SoP'], ['GFS']),
        f'{Block.MAIN}-SoP': State(
            actions.sort_pallets_by_weight_height_width,
            [f'{Block.MAIN}-SoZ'], ['GFS']),
        f'{Block.MAIN}-SoZ': State(
            actions.sort_available_zones_by_area_and_height,
            [f'{Block.MAIN}-SNZ'], ['GFS']),
        f'{Block.MAIN}-CBaU': State(
            actions.find_suitable_beams_and_upright,
            [f'{Block.MAIN}-RZC-90', f'{Block.MAIN}-PRZ-RS'],
            [f'{Block.MAIN}-SNZ']),
        f'{Block.MAIN}-RZC-90': State(
            actions.rotate_everything_90_clockwise,
            [f'{Block.MAIN}-PRZ-RS'], ['GFS']),
        f'{Block.MAIN}-RZCC-90': State(
            actions.rotate_evetything_90_counterclockwise,
            [f'{Block.MAIN}-SpZ'], ['GFS']),
        f'{Block.MAIN}-PRZ-RS': State(
            actions.place_road_zone_on_right_size,
            [f'{Block.MAIN}-PHG'], ['GFS']),
        f'{Block.MAIN}-PHG': State(
            actions.place_horizontal_rack_group,
            [f'{Block.MAIN}-CES-HG'], ['GFS']),
        f'{Block.MAIN}-CES-HG': State(
            actions.assert_current_rack_fits_available_zone,
            [f'{Block.CF}-SNRTS'], [f'{Block.MAIN}-DFS']),
        f'{Block.MAIN}-DFS': State(
            actions.decrease_current_frame_length,
            [f'{Block.MAIN}-CES-HG'], [f'{Block.MAIN}-RZCC-90-2']),
        f'{Block.MAIN}-SNZ': State(
            actions.set_next_zone,
            [f'{Block.MAIN}-GCOZARZ'], [f'{Block.MAIN}-SZZ']),
        f'{Block.MAIN}-GCOZARZ': State(
            actions.set_current_occupied_zones_and_road_zones,
            [f'{Block.MAIN}-CBaU'], ['GFS']),
        f'{Block.MAIN}-SZZ': State(
            actions.set_zero_zone,
            [f'{Block.MAIN}-GNC'], ['GFS']),
        f'{Block.MAIN}-GNC': State(
            actions.set_next_pallet,
            [f'{Block.MAIN}-GCOZARZ'], ['TS']),
        f'{Block.MAIN}-SpZ': State(
            actions.split_available_zone,
            [f'{Block.MAIN}-SoZ'], [f'{Block.MAIN}-SNZ']),
        f'{Block.MAIN}-RZCC-90-2': State(
            actions.rotate_evetything_90_counterclockwise,
            [f'{Block.MAIN}-SNZ'], ['GFS']),
    }


def get_rack_placement_states() -> dict[str, State]:
    return {
        f'{Block.RACK_PLACEMENT}-CTNOZ': State(
            actions.assert_current_rack_intersecting_occupied_zones,
            [f'{Block.GOOZ}-DLF', f'{Block.JOOZ}-DLF',
             f'{Block.DSFX}-IDR', f'{Block.EOZ}-IDR',
             f'{Block.MSR}-IDR'],
            [f'{Block.RACK_PLACEMENT}-CNTRZ']),
        f'{Block.RACK_PLACEMENT}-CNTRZ': State(
            actions.assert_current_rack_intersecting_road_zones,
            [f'{Block.RACK_PLACEMENT}-CIRH'],
            [f'{Block.RACK_PLACEMENT}-IPC']),
        f'{Block.RACK_PLACEMENT}-IPC': State(
            actions.increase_pallet_counter,
            [f'{Block.RACK_PLACEMENT}-CIEP'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-CIEP': State(
            actions.assert_current_pallets_are_enough,
            [f'{Block.RACK_PLACEMENT}-SNF'],
            [f'{Block.RACK_PLACEMENT}-SR-CC']),
        f'{Block.RACK_PLACEMENT}-GNC': State(
            actions.set_next_pallet,
            [f'{Block.MAIN}-RZCC-90'],
            [f'{Block.RACK_PLACEMENT}-RZCC-90-3']),
        f'{Block.RACK_PLACEMENT}-SR-CC': State(
            actions.save_rack,
            [f'{Block.RACK_PLACEMENT}-SRG-CC'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-SRG-CC': State(
            actions.save_rack_group,
            [f'{Block.RACK_PLACEMENT}-GNC'],
            [f'{Block.RACK_PLACEMENT}-GNC']),
        f'{Block.RACK_PLACEMENT}-SNF': State(
            actions.place_new_frame,
            [f'{Block.RACK_PLACEMENT}-CESFFR'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-CESFFR': State(
            actions.assert_current_rack_fits_available_zone,
            [f'{Block.RACK_PLACEMENT}-CTNOZ'],
            [f'{Block.RACK_PLACEMENT}-DLF']),
        f'{Block.RACK_PLACEMENT}-DLF': State(
            actions.delete_last_frame,
            [f'{Block.RACK_PLACEMENT}-SR'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-SR': State(
            actions.save_rack,
            [f'{Block.RACK_PLACEMENT}-SNLH-DEF'],
            [f'{Block.RACK_PLACEMENT}-SNLH-DEF']),
        f'{Block.RACK_PLACEMENT}-SNLH-DEF': State(
            actions.set_next_rack_position_higher_default,
            [f'{Block.CF}-SNRTD'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-CDR': State(
            actions.place_new_double_rack,
            [f'{Block.RACK_PLACEMENT}-CESFFH'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-CESFFH': State(
            actions.assert_current_rack_fits_available_zone,
            [f'{Block.RACK_PLACEMENT}-CTNOZ'],
            [f'{Block.RACK_PLACEMENT}-DD2R']),
        f'{Block.RACK_PLACEMENT}-DD2R': State(
            actions.swap_double_rack_to_single_rack,
            [f'{Block.RACK_PLACEMENT}-CESFFH'],
            [f'{Block.RACK_PLACEMENT}-SRG']),
        f'{Block.RACK_PLACEMENT}-SRG': State(
            actions.save_rack_group,
            [f'{Block.MAIN}-RZCC-90'],
            [f'{Block.MAIN}-RZCC-90']),
        f'{Block.RACK_PLACEMENT}-CIRH': State(
            actions.assert_intersected_road_horizontal,
            [f'{Block.RACK_PLACEMENT}-MRV'],
            [f'{Block.RACK_PLACEMENT}-IFLEFR']),
        f'{Block.RACK_PLACEMENT}-MRV': State(
            actions.move_current_rack_verticaly,
            [f'{Block.RACK_PLACEMENT}-CESFFH'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-IFLEFR': State(
            actions.assert_current_shelf_length_enough_for_road,
            [f'{Block.RACK_PLACEMENT}-ICZHEFRB'],
            [f'{Block.JOOZ}-DLF']),
        f'{Block.RACK_PLACEMENT}-ICZHEFRB': State(
            actions.assert_current_zone_height_enough_for_rack_bridge,
            [f'{Block.RACK_PLACEMENT}-SCFAS'],
            [f'{Block.JOOZ}-DLF']),
        f'{Block.RACK_PLACEMENT}-SCFAS': State(
            actions.set_current_frame_as_special,
            [f'{Block.RACK_PLACEMENT}-SDFS'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-SDFS': State(
            actions.set_default_frame_size,
            [f'{Block.RACK_PLACEMENT}-IPC'],
            ['GFS']),
        f'{Block.RACK_PLACEMENT}-RZCC-90-3': State(
            actions.rotate_evetything_90_counterclockwise,
            ['TS'], ['GFS']),
    }


def get_gooz_states() -> dict[str, State]:
    return {
        f'{Block.GOOZ}-DLF': State(
            actions.delete_last_frame,
            [f'{Block.GOOZ}-SR'],
            ['GFS']),
        f'{Block.GOOZ}-SR': State(
            actions.save_rack,
            [f'{Block.GOOZ}-SNLH-OZ'],
            ['GFS']),
        f'{Block.GOOZ}-SNLH-OZ': State(
            actions.set_next_rack_position_higher_oz,
            [f'{Block.CF}-SNRTD'],
            ['GFS']),
    }


def get_jooz_states() -> dict[str, State]:
    return {
        f'{Block.JOOZ}-DLF': State(
            actions.delete_last_frame,
            [f'{Block.JOOZ}-SR'],
            ['GFS']),
        f'{Block.JOOZ}-SR': State(
            actions.save_rack,
            [f'{Block.JOOZ}-SNLR'],
            ['GFS']),
        f'{Block.JOOZ}-SNLR': State(
            actions.set_next_rack_position_righter,
            [f'{Block.CF}-CNR-2'],
            ['GFS']),
    }


def get_dsfx_states() -> dict[str, State]:
    return {
        f'{Block.DSFX}-IDR': State(
            actions.assert_current_rack_is_double,
            [f'{Block.DSFX}-IBRI'],
            [f'{Block.DSFX}-DFS-R']),
        f'{Block.DSFX}-IBRI': State(
            actions.assert_both_racks_intersecting_occupied_zone,
            [f'{Block.DSFX}-DFS-RB'],
            [f'{Block.DSFX}-IFRI', f'{Block.DSFX}-ISRI']),
        f'{Block.DSFX}-DFS-R': State(
            actions.decrease_current_frame_length,
            [f'{Block.DSFX}-CTNOZ-DFS'],
            ['TS-DEL']),
        f'{Block.DSFX}-DFS-RB': State(
            actions.decrease_current_frame_length,
            [f'{Block.DSFX}-CTNOZ-DFS'],
            ['TS-DEL']),
        f'{Block.DSFX}-IFRI': State(
            actions.assert_first_rack_intersecting_occupied_zone,
            [f'{Block.DSFX}-DFS-R1'],
            ['TS-DEL']),
        f'{Block.DSFX}-ISRI': State(
            actions.assert_second_rack_intersecting_occupied_zone,
            [f'{Block.DSFX}-DFS-R2'],
            ['TS-DEL']),
        f'{Block.DSFX}-DFS-R1': State(
            actions.decrease_first_rack_frame_length,
            [f'{Block.DSFX}-CTNOZ-DFS'],
            ['TS-DEL']),
        f'{Block.DSFX}-DFS-R2': State(
            actions.decrease_second_rack_frame_length,
            [f'{Block.DSFX}-CTNOZ-DFS'],
            ['TS-DEL']),
        f'{Block.DSFX}-CTNOZ-DFS': State(
            actions.assert_current_rack_intersecting_occupied_zones,
            [f'{Block.DSFX}-IDR'],
            [f'{Block.RACK_PLACEMENT}-CNTRZ']
        )
    }


def get_eoz_states() -> dict[str, State]:
    return {
        f'{Block.EOZ}-IDR': State(
            actions.assert_current_rack_is_double,
            [f'{Block.EOZ}-IBRI'], [f'{Block.EOZ}-COZ']),
        f'{Block.EOZ}-IBRI': State(
            actions.assert_both_racks_intersecting_occupied_zone,
            ['TS-DEL'], [f'{Block.EOZ}-IFRI', f'{Block.EOZ}-ISRI']),
        f'{Block.EOZ}-COZ': State(
            actions.assert_last_rack_shelf_covers_occupied_zone,
            [f'{Block.EOZ}-DR'], ['TS-DEL']),
        f'{Block.EOZ}-DR': State(
            actions.disable_last_frame,
            [f'{Block.RACK_PLACEMENT}-CNTRZ'],
            ['GFS']),
        f'{Block.EOZ}-IFRI': State(
            actions.assert_first_rack_intersecting_occupied_zone,
            [f'{Block.EOZ}-COZ-R1'], ['TS-DEL']),
        f'{Block.EOZ}-ISRI': State(
            actions.assert_second_rack_intersecting_occupied_zone,
            [f'{Block.EOZ}-COZ-R2'], ['TS-DEL']),
        f'{Block.EOZ}-COZ-R1': State(
            actions.assert_last_shelf_of_first_rack_covers_occupied_zone,
            [f'{Block.EOZ}-DR-R1'],
            ['GFS']),
        f'{Block.EOZ}-COZ-R2': State(
            actions.assert_last_shelf_of_second_rack_covers_occupied_zone,
            [f'{Block.EOZ}-DR-R2'],
            ['GFS']),
        f'{Block.EOZ}-DR-R1': State(
            actions.disable_last_frame_for_first_rack,
            [f'{Block.RACK_PLACEMENT}-CNTRZ'],
            ['GFS']),
        f'{Block.EOZ}-DR-R2': State(
            actions.disable_last_frame_for_second_rack,
            [f'{Block.RACK_PLACEMENT}-CNTRZ'],
            ['GFS'])
    }


def get_coarse_fill_states() -> dict[str, State]:
    return {
        f'{Block.CF}-SNRTS': State(
            actions.set_next_rack_type_single,
            [f'{Block.CF}-FwF'],
            ['GFS']),
        f'{Block.CF}-FwF': State(
            actions.fill_with_frames,
            [f'{Block.CF}-CTNOZpCNTRZ'],
            ['GFS']),
        f'{Block.CF}-CTNOZpCNTRZ': State(
            actions.assert_current_rack_not_intersecting_oz_or_rz,
            [f'{Block.CF}-CIEP-1'],
            [f'{Block.CF}-DEF-1']),
        f'{Block.CF}-CIEP-1': State(
            actions.assert_current_pallets_are_enough_for_rack,
            [f'{Block.CF}-IPC-1'],
            [f'{Block.CF}-DEF-2']),
        f'{Block.CF}-IPC-1': State(
            actions.increase_pallet_counter_for_rack,
            [f'{Block.CF}-SR'],
            ['GFS']),
        f'{Block.CF}-SR': State(
            actions.save_rack,
            [f'{Block.CF}-SNLH-DEF'],
            ['GFS']),
        f'{Block.CF}-SNLH-DEF': State(
            actions.set_next_rack_position_higher_default,
            [f'{Block.CF}-SNRTD'],
            ['GFS']),
        f'{Block.CF}-SNRTD': State(
            actions.set_next_rack_type_double,
            [f'{Block.CF}-CNR'],
            ['GFS']),
        f'{Block.CF}-CNR': State(
            actions.create_new_rack,
            [f'{Block.CF}-CESFF'],
            ['GFS']),
        f'{Block.CF}-CESFF': State(
            actions.assert_current_rack_fits_available_zone,
            [f'{Block.CF}-FwF'],
            [f'{Block.RACK_PLACEMENT}-CESFFH']),
        f'{Block.CF}-DEF-1': State(
            actions.delete_excess_frames_oz,
            [f'{Block.CF}-CIEP-2'],
            ['GFS']),
        f'{Block.CF}-DEF-2': State(
            actions.delete_excess_frames_pl,
            [f'{Block.CF}-IPC-2'],
            ['GFS']),
        f'{Block.CF}-CIEP-2': State(
            actions.assert_current_pallets_are_enough_for_rack,
            [f'{Block.CF}-IPC-2'],
            [f'{Block.CF}-DEF-2']),
        f'{Block.CF}-IPC-2': State(
            actions.increase_pallet_counter_for_rack,
            [f'{Block.RACK_PLACEMENT}-SNF'],
            ['GFS']),
        f'{Block.CF}-CNR-2': State(
            actions.create_new_rack,
            [f'{Block.CF}-CESFF-2'],
            ['GFS']),
        f'{Block.CF}-CESFF-2': State(
            actions.assert_current_rack_fits_available_zone,
            [f'{Block.CF}-FwF'],
            [f'{Block.CF}-SNLH-DEF']),
    }


def get_msr_states() -> dict[str, State]:
    return {
        f'{Block.MSR}-IDR': State(
            actions.assert_current_rack_is_double,
            [f'{Block.MSR}-IFRI'], ['TS-DEL']),
        f'{Block.MSR}-IFRI': State(
            actions.assert_first_rack_intersecting_occupied_zone,
            ['TS-DEL'], [f'{Block.MSR}-MSRH']
        ),
        f'{Block.MSR}-MSRH': State(
            actions.move_second_rack_higher_over_oz,
            [f'{Block.RACK_PLACEMENT}-CESFFH'],
            ['GFS']),
    }


class StateMachine:
    def __init__(self, reference_book):
        self.states = self.__compile_states()
        self.reference_book = reference_book

    def __compile_states(self) -> dict[str, State]:
        states = {}
        states.update(get_general_states())
        states.update(get_main_loop_states())
        states.update(get_rack_placement_states())
        states.update(get_gooz_states())
        states.update(get_jooz_states())
        states.update(get_dsfx_states())
        states.update(get_eoz_states())
        states.update(get_coarse_fill_states())
        states.update(get_msr_states())
        return states

    def get_initial_state(self) -> State:
        return self.states[f'{Block.MAIN}-S']

    def get_end_normal_state(self) -> State:
        return self.states['TS']

    def get_end_failure_state(self) -> State:
        return self.states['GFS']

    def get_end_delete_state(self) -> State:
        return self.states['TS-DEL']

    # @visualize_solution_decorator
    def apply_action(self, solution: Solution) -> Solution:
        try:
            current_state = solution.state
            action_function = current_state.process_function
            action_function(self.reference_book, solution)
            solution.action_status = ActionStatus.SUCCESS
        except ActionFailure as e:
            # print(f"Regular action fail: {e.message}")
            solution.action_status = ActionStatus.FAILED
        except Exception as e:
            print(f"Critical action fail: {e}")
        return solution

    def choose_next_action(self, solution: Solution) -> list[Solution]:
        current_state = solution.state
        next_success_states = current_state.next_success_state_name_list
        next_failure_states = current_state.next_failure_state_name_list

        if solution.action_status == ActionStatus.SUCCESS:
            next_states = next_success_states
        elif solution.action_status == ActionStatus.FAILED:
            next_states = next_failure_states
        elif solution.action_status == ActionStatus.NOT_STARTED:
            return [solution]
        else:
            raise ValueError("Unknown action status")

        new_solutions = []

        for next_state_name in next_states:
            next_state = self.states.get(next_state_name)
            if next_state is None:
                raise ValueError(f"State '{next_state_name}' not found")

            new_solution = deepcopy(solution)
            new_solution.state = next_state
            new_solution.action_status = ActionStatus.NOT_STARTED
            # new_solution.state_history.append(next_state_name)
            new_solutions.append(new_solution)

        return new_solutions

    def remove_invalid_solutions(self, solutions: list[Solution]
                                 ) -> list[Solution]:
        valid_solutions = []

        for solution in solutions:
            if solution.state == self.get_end_failure_state():
                continue
            elif solution.state == self.get_end_delete_state():
                continue
            valid_solutions.append(solution)

        return valid_solutions

    def extract_end_solutions(self, solutions: list[Solution]
                              ) -> list[Solution]:
        transitional_solutions = []
        end_solutions = []

        for solution in solutions:
            if solution.state == self.get_end_normal_state():
                end_solutions.append(solution)
            else:
                transitional_solutions.append(solution)

        return transitional_solutions, end_solutions
