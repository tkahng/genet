import polyline
import s2sphere as s2
import networkx as nx
import numpy as np
import statistics

APPROX_EARTH_RADIUS = 6371008.8
S2_LEVELS_FOR_SPATIAL_INDEXING = [0, 6, 8, 12, 18, 24, 30]


def decode_polyline_to_s2_points(_polyline):
    """
    :param _polyline: google encoded polyline
    :return:
    """
    decoded = polyline.decode(_polyline)
    return [grab_index_s2(lat, lon) for lat, lon in decoded]


def compute_average_proximity_to_polyline(poly_1, poly_2):
    """
    Computes average distance between points in poly_1 and closest points in poly_2. Works best when poly_1 is less
    dense with points than poly_2.
    :param poly_1: google encoded polyline
    :param poly_2: google encoded polyline
    :return:
    """
    s2_poly_list_1 = decode_polyline_to_s2_points(poly_1)
    s2_poly_list_2 = decode_polyline_to_s2_points(poly_2)

    closest_distances = []
    for point in s2_poly_list_1:
        d = None
        for other_line_point in s2_poly_list_2:
            dist = distance_between_s2cellids(point, other_line_point)
            if (d is None) or (d > dist):
                d = dist
        closest_distances.append(d)
    return statistics.mean(closest_distances)


def grab_index_s2(lat, lng):
    """
    Returns s2.CellID from lat and lon
    :param lat
    :param lng
    :return:
    """
    return s2.CellId.from_lat_lng(s2.LatLng.from_degrees(lat, lng)).id()


def distance_between_s2cellids(s2cellid1, s2cellid2):
    if isinstance(s2cellid1, int):
        s2cellid1 = s2.CellId(s2cellid1)
    elif isinstance(s2cellid1, np.int64):
        s2cellid1 = s2.CellId(int(s2cellid1))
    if isinstance(s2cellid2, int):
        s2cellid2 = s2.CellId(s2cellid2)
    elif isinstance(s2cellid2, np.int64):
        s2cellid2 = s2.CellId(int(s2cellid2))
    distance = s2cellid1.to_lat_lng().get_distance(s2cellid2.to_lat_lng()).radians
    return distance * APPROX_EARTH_RADIUS


def change_proj(x, y, crs_transformer):
    return crs_transformer.transform(x, y)


def find_closest_nodes(graph, s2_id, distance):
    """
    finds nodes within `distance` in meters from s2_cell_id. Nodes are assumed to have s2_id attributes
    :param graph:
    :return: list of node ids
    """
    neighbourhood_of_node = create_subsetting_area(CellIds=[s2_id],
                                                   angle=(distance / APPROX_EARTH_RADIUS))
    return [id for id, s2_id in graph.nodes(data='s2_id') if
            neighbourhood_of_node.may_intersect(s2.Cell(s2.CellId(s2_id)))]


def find_edges_from_cell_to_root(node_id, cell_id):
    edges_to_add = []
    cell = s2.CellId(cell_id)
    edges_to_add.append((cell_id, node_id))
    for i in range(len(S2_LEVELS_FOR_SPATIAL_INDEXING) - 1):
        edges_to_add.append((cell.parent(S2_LEVELS_FOR_SPATIAL_INDEXING[i]).id(),
                             cell.parent(S2_LEVELS_FOR_SPATIAL_INDEXING[i + 1]).id()))
    # add the connection to the super cell
    edges_to_add.append((0, cell.parent(S2_LEVELS_FOR_SPATIAL_INDEXING[0]).id()))
    return edges_to_add


def index_nodes(graph_nodes):
    edges_to_add = []
    nodes_to_add = {}
    # index edges
    for node_id, node_attrib in graph_nodes:
        s2_indexing_edges = find_edges_from_cell_to_root(node_id, node_attrib['s2_id'])
        edges_to_add.extend(s2_indexing_edges)
        for from_id_e, to_id_e in s2_indexing_edges:
            nodes_to_add = add_or_update_indexing_edges_attr_dict(from_id_e, node_attrib, nodes_to_add)
            nodes_to_add = add_or_update_indexing_edges_attr_dict(to_id_e, node_attrib, nodes_to_add)
    return edges_to_add, nodes_to_add


def add_or_update_indexing_edges_attr_dict(node, edge_attr, nodes_to_add):
    if (node in nodes_to_add.keys()) and isinstance(node, int):
        for k, v in nodes_to_add[node].items():
            if isinstance(v, list):
                if k not in edge_attr.keys():
                    nodes_to_add[node][k] = list(set(v))
                else:
                    nodes_to_add[node][k] = list(set(v) | set(edge_attr[k]))
    else:
        nodes_to_add[node] = edge_attr.copy()
    return nodes_to_add


def create_subsetting_area(CellIds, angle=0, buffer_multiplier=None):
    """
    Builds a bounding s2.Cap covering the CellIds + `angle` value buffer
    finds a midpoint from the points passed and uses the largest distance as minimal radius for the neighbourhood,
    if just one point, that distance is zero and angle is needed to specify the radius for the cap.
    Can also specify angle == 'double' to use the largest distance as buffer
    :param CellIds:
    :param angle: angle/distance for buffer
    :param buffer_multiplier: float, use the largest distance between points as a buffer for the area,
     final radius for the Cap = largest distance * buffer_multiplier + angle  OR
     final radius for the Cap = largest distance + largest distance * buffer_multiplier + angle (if the multiplier is
     less than 1, the subsetting area has to at least cover the points passed to generate the area)
    :return: s2.Cap
    """

    def sum_pts(pts):
        p = None
        for p_n in pts:
            if p is None:
                p = p_n
            else:
                p = p + p_n
        return p

    pts = [s2.CellId(p).to_point() for p in CellIds]

    if len(pts) > 1:
        # find a midpoint and distance dist to the farthest point
        pts = [s2.CellId(p).to_point() for p in CellIds]
        mid_point = sum_pts(pts).normalize()
        dist = 0
        for p in pts:
            d = s2.LatLng.from_point(mid_point).get_distance(s2.LatLng.from_point(p)).radians
            if d > dist:
                dist = d
    else:
        mid_point = pts[0]
        dist = 0

    if buffer_multiplier is not None:
        if buffer_multiplier < 1:
            dist = dist + (dist * buffer_multiplier)
        else:
            dist = dist * buffer_multiplier

    if isinstance(angle, s2.Angle):
        angle = angle + s2.Angle.from_radians(dist)
    else:
        angle = s2.Angle.from_radians(angle + dist)
    area = s2.Cap.from_axis_angle(mid_point, angle)

    return area


class SpatialTree(nx.DiGraph):
    """
    Class which represents a nx.MultiDiGraph nodes as a spatial tree
    hierarchy based on s2 cell levels
    """

    def __init__(self, nodes=None):
        super().__init__()
        if nodes is not None:
            self.add_nodes(nodes)

    def add_nodes(self, nodes):
        """
        Indexes each link and adds to the graph
        :param nodes: [('nodes', {'s2_id': 12345, 'attribs': 'cool_node_bro'}), ...]
        :return:
        """

        edges_to_add, nodes_to_add = index_nodes(nodes)

        for node, data in nodes_to_add.items():
            self.add_node(node, **data)
        self.add_edges_from(list(set(edges_to_add)))

    def leaves(self):
        return [x for x in self.nodes() if self.is_graph_node(x)]

    def is_graph_node(self, node):
        return self.out_degree(node) == 0

    def roots(self):
        return [0]

    def find_closest_nodes(self, s2_cell, distance_radius):
        angle = distance_radius / APPROX_EARTH_RADIUS

        closest_nodes_to_cell = []

        def check_children(parent):
            for parent, kid in self.edges(parent):
                if self.is_graph_node(kid):
                    closest_nodes_to_cell.append(kid)
                elif neighbourhood_of_g_node.may_intersect(s2.Cell(s2.CellId(kid))):
                    check_children(kid)

        neighbourhood_of_g_node = create_subsetting_area(CellIds=[s2_cell], angle=angle)
        for root in self.roots():
            check_children(root)

        return closest_nodes_to_cell
