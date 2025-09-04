import numpy as np
import plotly.graph_objects as go

from src.pallet_packer.solution import Solution
from src.rack import DoubleRack, Rack
from src.utils import check_if_debugger_is_active
from src.zone import AvailableZone, OccupiedZone, SpecialRoadZone


def visualize_solution_decorator(func: callable) -> callable:
    """Decorator to visualize the solution if the debugger is active.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The decorated function.
    """
    def wrapper(*args, **kwargs):
        solution = func(*args, **kwargs)
        if check_if_debugger_is_active():
            visualize_solution(solution)
        return solution
    return wrapper


def visualize_solution(solution: Solution) -> None:
    """Visualizes the solution using Plotly.
    Args:
        solution (Solution): The solution to visualize.
    """
    fig = go.Figure()

    plot_available_zones(fig, solution.initial_available_zones)
    plot_occupied_zones(fig, solution.occupied_zones)
    plot_special_road_zones(fig, solution.road_zones)

    for rack_group in solution.saved_rack_groups:
        for rack in rack_group.racks:
            plot_racks(fig, rack)

    fig.update_layout(title='Pallet Packer Solution Visualization',
                      xaxis_title='X Axis',
                      yaxis_title='Y Axis',
                      showlegend=True)
    fig.update_yaxes(
        scaleanchor="x",
        scaleratio=1,
    )

    remove_duplicate_names(fig)

    fig.show()


def plot_available_zones(fig: go.Figure,
                         available_zones: list[AvailableZone]) -> None:
    """Plots the available zones on the figure.
    Args:
        fig (go.Figure): The Plotly figure to add the zones to.
        available_zones (list[AvailableZone]): The list of available zones.
    """

    for zone in available_zones:
        polygon = zone.contour.exterior.xy
        fig.add_trace(go.Scatter(
            x=np.array(polygon[0]),
            y=np.array(polygon[1]),
            mode='lines',
            fill='toself',
            fillcolor='rgba(0, 255, 0, 0.5)',
            line=dict(color='green'),
            name='Available Zone'
        ))


def plot_occupied_zones(fig: go.Figure,
                        occupied_zones: list[OccupiedZone]) -> None:
    """Plots the occupied zones on the figure.

    Args:
        fig (go.Figure): The Plotly figure to add the zones to.
        occupied_zones (list[OccupiedZone]): The list of occupied zones.
    """

    for zone in occupied_zones:
        polygon_zone = zone.contour.exterior.xy

        fig.add_trace(go.Scatter(
            x=np.array(polygon_zone[0]),
            y=np.array(polygon_zone[1]),
            mode='lines',
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.5)',
            line=dict(color='red'),
            name='Occupied Zone'
        ))


def plot_special_road_zones(fig: go.Figure,
                            special_road_zones: list[SpecialRoadZone]) -> None:
    """Plots the special road zones on the figure.

    Args:
        fig (go.Figure): The Plotly figure to add the zones to.
        special_road_zones (list[SpecialRoadZone]): The list of special
            road zones.
    """

    for zone in special_road_zones:
        polygon = zone.contour.exterior.xy
        fig.add_trace(go.Scatter(
            x=np.array(polygon[0]),
            y=np.array(polygon[1]),
            mode='lines',
            fill='toself',
            fillcolor='rgba(0, 0, 255, 0.5)',
            line=dict(color='blue'),
            name=f'Special Road Zone {zone}'
        ))


def plot_racks(fig: go.Figure, rack: list[Rack | DoubleRack]) -> None:
    """Plots the racks on the figure.

    Args:
        fig (go.Figure): The Plotly figure to add the racks to.
        rack (list[Rack  |  DoubleRack]): The list of racks to plot.
    """

    if isinstance(rack, Rack):
        plot_rack(fig, rack)
    elif isinstance(rack, DoubleRack):
        for single_rack in [rack.rack_1, rack.rack_2]:
            plot_rack(fig, single_rack)


def plot_rack(fig: go.Figure, rack: Rack):
    """Plots a single rack on the figure.
    Args:
        fig (go.Figure): The Plotly figure to add the rack to.
        rack (Rack): The rack to plot.
    """
    polygon = rack.contour.exterior.xy
    fig.add_trace(go.Scatter(
        x=np.array(polygon[0]),
        y=np.array(polygon[1]),
        mode='lines',
        fill='toself',
        fillcolor='rgba(128, 0, 128, 0.5)',
        line=dict(color='purple'),
        name='Rack'
    ))

    colors = ['indigo', 'magenta', 'cyan']
    for deck_idx, deck in enumerate(rack.decks):
        deck_polygon = deck.exterior.xy
        color = colors[rack.deck_status[deck_idx].value - 1]

        fig.add_trace(go.Scatter(
            x=np.array(deck_polygon[0]),
            y=np.array(deck_polygon[1]),
            mode='lines',
            fill='toself',
            fillcolor='rgba(75, 0, 130, 0.5)',
            line=dict(color=color),
            name=f'Deck {rack.deck_status[deck_idx].name}'
        ))


def remove_duplicate_names(fig: go.Figure) -> None:
    """Removes duplicate names from the figure traces.
    Args:
        fig (go.Figure): The Plotly figure to modify.
    """
    names = set()
    fig.for_each_trace(
        lambda trace:
            trace.update(showlegend=False)
            if (trace.name in names) else names.add(trace.name))
