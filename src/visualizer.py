from typing import List

import numpy as np
import plotly.graph_objects as go

from src.building import Building
from src.forbidden_zone import ForbiddenZone
from src.rack_group import RackGroup
from src.available_zone import AvailableZone


class Visualizer():
    def __init__(self, random_seed: int = 42):
        np.random.seed(random_seed)

        self.fig = None
        self.rack_colors = {}

    def generate_random_color(self) -> str:
        """Generate random color.

        Returns:
            str: Random color in the format 'rgb(r, g, b)'
        """
        return f'rgb{tuple(int(num) for num in np.random.rand(3,) * 255)}'

    def plot(self, building: List[Building], rack_groups: List[RackGroup],
             rack_zones: List[AvailableZone],
             forbiden_zones: List[ForbiddenZone] = []) -> None:
        """Plot the buildings, rack groups, rack zones and forbidden zones.

        Args:
            building (List[Building]): buildings
            rack_groups (List[RackGroup]): rack groups
            rack_zones (List[AvailableZone]): available zones for racks
            forbiden_zones (List[ForbiddenZone], optional): forbidden zones.
                Defaults to [].
        """
        self.fig = go.Figure()
        for b in building:
            self.fig.add_trace(go.Scatter(x=np.array(b.walls.exterior.xy[0]),
                                          y=np.array(b.walls.exterior.xy[1]),
                                          name='Здания',
                                          line=dict(color='black')))
            self.fig.add_trace(
                go.Scatter(x=np.array(b.available_space.exterior.xy[0]),
                           y=np.array(b.available_space.exterior.xy[1]),
                           name='Доступные места внутри зданий',
                           line=dict(color='black', dash='dash')))

        for zone in rack_zones:
            self.fig.add_trace(
                go.Scatter(x=np.array(zone.geometry.exterior.xy[0]),
                           y=np.array(zone.geometry.exterior.xy[1]),
                           name='Зоны для размещения стеллажей',
                           line=dict(color='green', dash='dash')))

        for zone in forbiden_zones:
            self.fig.add_trace(
                go.Scatter(x=np.array(zone.geometry.exterior.xy[0]),
                           y=np.array(zone.geometry.exterior.xy[1]),
                           name='Запрещенные зоны',
                           line=dict(color='red', dash='dash')))
            self.fig.add_trace(
                go.Scatter(
                    x=np.array(zone.geometry_with_clearance.exterior.xy[0]),
                    y=np.array(zone.geometry_with_clearance.exterior.xy[1]),
                    name='Запрещенные зоны с учетом зазора',
                    line=dict(color='red', dash='dot')))

        for rack_group in rack_groups:
            rack_group_id = rack_group.rack_section_info.id
            if rack_group_id not in self.rack_colors:
                self.rack_colors[rack_group_id] = self.generate_random_color()

            self.fig.add_trace(
                go.Scatter(
                    x=np.array(rack_group.physical_bounds.exterior.xy[0]),
                    y=np.array(rack_group.physical_bounds.exterior.xy[1]),
                    name='Физическая граница группы '
                    f'стеллажей типа {rack_group_id}',
                    line=dict(color=self.rack_colors[rack_group_id],
                              dash='dash')))
            self.fig.add_trace(
                go.Scatter(
                    x=np.array(rack_group.restrictive_bounds.exterior.xy[0]),
                    y=np.array(rack_group.restrictive_bounds.exterior.xy[1]),
                    name='Граница группы стеллажей типа '
                    f'{rack_group_id} с учётом зазора',
                    line=dict(color=self.rack_colors[rack_group_id],
                              dash='dot')))

            for rack in rack_group.racks:
                self.fig.add_trace(
                    go.Scatter(x=np.array(rack.get_exterior().xy[0]),
                               y=np.array(rack.get_exterior().xy[1]),
                               name=f'Стеллажи типа {rack_group_id}',
                               line=dict(color=self.rack_colors[
                                         rack_group_id])))
                shelfs_exteriors = rack.get_shelfs_exteriors()
                shelf_specials = np.array(rack.get_shelfs_special()).flatten()
                for sh_idx, shelf_exterior in enumerate(shelfs_exteriors):
                    self.fig.add_trace(
                        go.Scatter(x=np.array(shelf_exterior.xy[0]),
                                   y=np.array(shelf_exterior.xy[1]),
                                   name=f'Полки типа {rack_group_id}',
                                   line=dict(color=self.rack_colors[
                                             rack_group_id],
                                             )))
                    if shelf_specials[sh_idx]:
                        x_0 = min(shelf_exterior.xy[0])
                        x_1 = max(shelf_exterior.xy[0])
                        y_0 = min(shelf_exterior.xy[1])
                        y_1 = max(shelf_exterior.xy[1])
                        self.fig.add_trace(
                            go.Scatter(x=[x_0, x_1, x_1, x_0],
                                       y=[y_0, y_1, y_0, y_1],
                                       name='Специальные полки '
                                       f'типа {rack_group_id}',
                                       line=dict(color=self.rack_colors[
                                                 rack_group_id])))

                pillars_exteriors = rack.get_pillars_exteriors()
                for pillar_exterior in pillars_exteriors:
                    self.fig.add_trace(
                        go.Scatter(x=np.array(pillar_exterior.xy[0]),
                                   y=np.array(pillar_exterior.xy[1]),
                                   name=f'Стойки типа {rack_group_id}',
                                   line=dict(color=self.rack_colors[
                                             rack_group_id])))

        self.fig.update_layout(showlegend=True)

        included_names = set()
        self.fig.for_each_trace(
            lambda trace:
                trace.update(showlegend=False)
                if (trace.name in included_names)
                else included_names.add(trace.name))

    def show(self) -> None:
        """Show the plot.
        """
        self.fig.update_yaxes(
            scaleanchor="x",
            scaleratio=1,
        )
        self.fig.show()
