import logging
import genet.utils.routing as routing


def find_routes_for_schedule(network, snapping_distance):
    # modes sharing infrastructure, used for modal subgraphs for routing/snapping
    routing_mode_map = {
        'drive': {'bus', 'car'},
        'rail': {'rail', 'tram', 'subway', 'funicular'},
        'ferry': {'ferry'},
        'cable': {'gondola', 'cable car'}
    }
    schedule_modes = network.schedule.unique_modes()
    for mode_group_name, network_modes in routing_mode_map.items():
        if schedule_modes & network_modes:
            logging.info(f'Routing for subgraph: {mode_group_name}')
            # extract modal subgraph
            modal_subgraph = network.modal_subgraph(network_modes)
            if modal_subgraph.edges():
                # todo better identification of services based on modes
                for service_id, service in network.schedule.services.items():
                    if service.unique_modes() & network_modes:
                        find_routes_for_service(modal_subgraph, service, snapping_distance)
            else:
                logging.warning(f'Modal subgraph for {mode_group_name} is empty.')


def find_routes_for_service(network_graph, service, snapping_distance):
    service_g = routing.snap_and_route(network_graph, service, snapping_distance)
    if service_g is not None:
        for route in service.routes:
            network_route = []
            for stop_u, stop_v in zip(route.stops[:-1], route.stops[1:]):
                network_route = network_route + service_g[stop_u.id][stop_v.id]['network_route']
                # todo what happens if different services share stops? linkref ids could get overwritten (mintransfer
                # times)
                stop_u.linkRefId = service_g.nodes[stop_u.id]['linkRefId']
                stop_v.linkRefId = service_g.nodes[stop_v.id]['linkRefId']
            route.route = network_route
    else:
        logging.warning(f'Routing failed for Service: {service.id}')


def find_route_for_route(network_graph, route, snapping_distance):
    route_g = routing.snap_and_route(network_graph, route, snapping_distance)
    if route_g is not None:
        network_route = []
        for stop_u, stop_v in route_g.edges():
            network_route = network_route + route_g[stop_u][stop_v]['network_route']
        route.route = network_route
        for stop in route.stops:
            stop.linkRefId = route_g.nodes[stop.id]['linkRefId']
    else:
        logging.warning(f'Routing failed for Route: {route.id}')
