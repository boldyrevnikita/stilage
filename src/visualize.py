import numpy as np
import plotly.graph_objects as go
import shapely

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
    if solution is None or getattr(solution, 'saved_rack_groups', None) in (None, []):
        return fig
        
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
    """Plots a single rack on the figure with column intersection handling.
    
    Args:
        fig (go.Figure): The Plotly figure to add the rack to.
        rack (Rack): The rack to plot.
    """
    # Draw rack contour
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
    
    # ✅ CRITICAL DEBUG: Check rack attributes
    print(f"\n{'='*80}")
    print(f"[VISUALIZE_DEBUG] Plotting rack")
    print(f"[VISUALIZE_DEBUG] Rack type: {type(rack).__name__}")
    print(f"[VISUALIZE_DEBUG] Rack bounds: {rack.bounds}")
    print(f"[VISUALIZE_DEBUG] Number of decks: {len(rack.decks)}")
    
    # Check for is_protective attribute
    has_is_protective = hasattr(rack, 'is_protective')
    print(f"[VISUALIZE_DEBUG] hasattr(rack, 'is_protective'): {has_is_protective}")
    
    if has_is_protective:
        print(f"[VISUALIZE_DEBUG] rack.is_protective = {rack.is_protective}")
    
    # Check for protected_column attribute
    has_protected_column = hasattr(rack, 'protected_column')
    print(f"[VISUALIZE_DEBUG] hasattr(rack, 'protected_column'): {has_protected_column}")
    
    if has_protected_column:
        print(f"[VISUALIZE_DEBUG] rack.protected_column = {rack.protected_column}")
        print(f"[VISUALIZE_DEBUG] rack.protected_column is not None: {rack.protected_column is not None}")
        
        if rack.protected_column is not None:
            print(f"[VISUALIZE_DEBUG] Column bounds: {rack.protected_column.contour.bounds}")
    
    print(f"{'='*80}\n")
    
    # Draw decks with intersection check
    for deck_idx, deck in enumerate(rack.decks):
        should_skip = False
        deck_bounds = deck.bounds
        
        print(f"[VISUALIZE_DEBUG] Deck {deck_idx}: Y=[{deck_bounds[1]:.1f}, {deck_bounds[3]:.1f}]")
        
        # ✅ Check if this is a protective rack with a column
        if (hasattr(rack, 'is_protective') and rack.is_protective and 
            hasattr(rack, 'protected_column') and rack.protected_column is not None):
            
            column_bounds = rack.protected_column.contour.bounds
            
            # Check Y-coordinate overlap
            y_overlap = (deck_bounds[1] < column_bounds[3] and 
                        deck_bounds[3] > column_bounds[1])
            
            # Also check shapely intersection
            geom_intersects = shapely.intersects(deck, rack.protected_column.contour)
            
            print(f"[VISUALIZE_DEBUG]   Column Y=[{column_bounds[1]:.1f}, {column_bounds[3]:.1f}]")
            print(f"[VISUALIZE_DEBUG]   Y-overlap: {y_overlap}")
            print(f"[VISUALIZE_DEBUG]   Geom-intersects: {geom_intersects}")
            
            if y_overlap or geom_intersects:
                should_skip = True
                print(f"[VISUALIZE_DEBUG]   ✅ SKIPPING deck {deck_idx} (intersects with column)")
        
        if should_skip:
            continue
        
        # Draw the deck
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
        
        print(f"[VISUALIZE_DEBUG]   ✓ Drew deck {deck_idx}")


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