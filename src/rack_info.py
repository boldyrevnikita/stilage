class RackInfo:
    def __init__(self, id: int, length: float, width: float, height: float,
                 abs_quantity: int, min_quantity: int, max_quantity: int,
                 rel_quantity: float,
                 side_connection_distance: float,
                 back_connection_distance: float,
                 front_distance: float,
                 back_distance: float, side_distance: float):
        self.id = id
        self.length = length
        self.width = width
        self.height = height
        self.abs_quantity = abs_quantity
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity
        self.rel_quantity = rel_quantity
        self.quantity_left = abs_quantity
        self.side_connection_distance = side_connection_distance
        self.back_connection_distance = back_connection_distance
        self.front_distance = front_distance
        self.back_distance = back_distance
        self.side_distance = side_distance
