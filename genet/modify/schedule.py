import genet.utils.routing as routing


def find_routes_for_schedule(network, snapping_distance):
    pass


def find_routes_for_service(network_graph, service, snapping_distance):
    pass


def find_route_for_route(network_graph, route, snapping_distance):
    # TODO modal network subgraph
    route_g = routing.snap_and_route(network_graph, route, snapping_distance)
    network_route = []
    for stop_u, stop_v in route_g.edges():
        network_route = network_route + route_g[stop_u][stop_v]['network_route']
    route.route = network_route
    for stop in route.stops:
        stop.linkRefId = route_g.nodes[stop.id]['linkRefId']
