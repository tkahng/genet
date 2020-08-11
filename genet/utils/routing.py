from pyomo.environ import *  # noqa: F403
import itertools
import networkx as nx
import logging
import genet.utils.spatial as spatial
import genet.utils.graph_operations as graph_operations


def snap_and_route(network_graph, schedule_element, snapping_distance, solver):
    """
    :param network_graph: modal subgraph of genet network
    :param schedule_element: route, service or schedule (not recommended)
    :param snapping_distance: in meters, area to search for nearest nodes for stops
    :return:
    """
    problem_g, schedule_g = build_graph_for_maximum_stable_set_problem(network_graph, schedule_element,
                                                                       snapping_distance)
    if problem_g is None:
        return None
    solution = set_up_and_solve_model(problem_g, solver)
    nx.set_node_attributes(schedule_g, solution)
    # generate route(s)
    for stop_u, stop_v in schedule_g.edges():
        nodes = nx.dijkstra_path(
            network_graph,
            schedule_g.nodes[stop_u]['closest_node'],
            schedule_g.nodes[stop_v]['closest_node']
        )
        network_route = [
            graph_operations.find_shortest_path_link(dict(network_graph[node_u][node_v]), modes=schedule_g.mode) for
            node_u, node_v in zip(nodes[:-1], nodes[1:])]
        if 'linkRefId' not in schedule_g.nodes[stop_u]:
            schedule_g.nodes[stop_u]['linkRefId'] = network_route[0]
        elif network_route[0] != schedule_g.nodes[stop_u]['linkRefId']:
            network_route = [schedule_g.nodes[stop_u]['linkRefId']] + network_route
        if 'linkRefId' not in schedule_g.nodes[stop_v]:
            schedule_g.nodes[stop_v]['linkRefId'] = network_route[-1]
        elif network_route[-1] != schedule_g.nodes[stop_v]['linkRefId']:
            network_route.append(schedule_g.nodes[stop_v]['linkRefId'])
        schedule_g[stop_u][stop_v]['network_route'] = network_route
    return schedule_g


def build_graph_for_maximum_stable_set_problem(network_graph, schedule_element, snapping_distance):
    """
    Extension to the Route/Service/Schedule graph:
        nodes: network's graph nodes that are closest to stops
            each node has attribute c which is a coefficient
            describing spatial proximity of the node to the stop
            and average shortest path length from and to that node
        edges: connections between nodes if they are in the same
            selection pool or there is no path between them
    :return:
    """
    problem_g = nx.DiGraph()
    schedule_g = schedule_element.build_graph()
    message = f'Building Problem Graph for {schedule_element.__class__.__name__}'
    if 'id' in schedule_element.__dict__:
        message = message + f' id: {schedule_element.id}'
    logging.info(message)
    for node_id, s2_id in schedule_g.nodes(data='s2_id'):
        # TODO parallelise closest node finding (all schedule stops at once)
        closest_nodes = spatial.find_closest_nodes(network_graph, s2_id, snapping_distance)
        if not closest_nodes:
            # TODO failure conditions when no closest nodes
            logging.warning(f'One of the stops: {node_id} has found no network nodes within the specified threshold')
            return None, None
        closest_nodes = [f'{node}-{node_id}' for node in closest_nodes]
        problem_g.add_nodes_from(closest_nodes, total_path_lengths=0, total_paths=0, stop_id=node_id)
        problem_g.add_edges_from(itertools.combinations(closest_nodes, 2))
        schedule_g.nodes[node_id]['closest_nodes'] = closest_nodes

    logging.info('Computing shortest paths')
    for u, v in schedule_g.edges():
        for problem_g_u_closest_node in schedule_g.nodes[u]['closest_nodes']:
            for problem_g_v_closest_node in schedule_g.nodes[v]['closest_nodes']:
                u_closest_node = problem_g_u_closest_node.split('-')[0]
                v_closest_node = problem_g_v_closest_node.split('-')[0]
                try:
                    path_len = nx.dijkstra_path_length(network_graph, u_closest_node, v_closest_node, weight='length')
                    problem_g.nodes[problem_g_u_closest_node]['total_path_lengths'] += path_len
                    problem_g.nodes[problem_g_u_closest_node]['total_paths'] += 1
                    problem_g.nodes[problem_g_v_closest_node]['total_path_lengths'] += path_len
                    problem_g.nodes[problem_g_v_closest_node]['total_paths'] += 1
                except nx.NetworkXNoPath:
                    problem_g.add_edge(problem_g_u_closest_node, problem_g_v_closest_node)

    # check there are closest nodes left for each stop
    for u, v in schedule_g.edges():
        node_degrees = [problem_g.out_degree(c_node) + problem_g.in_degree(c_node) for c_node in
            schedule_g.nodes[u]['closest_nodes']]
        node_degrees = node_degrees + [problem_g.out_degree(c_node) + problem_g.in_degree(c_node) for c_node in
            schedule_g.nodes[v]['closest_nodes']]
        total_nodes = len(schedule_g.nodes[u]['closest_nodes']) + len(schedule_g.nodes[v]['closest_nodes'])
        if all([node_degree >= total_nodes - 1 for node_degree in node_degrees]):
            logging.warning(
                f'Two stops: {u} and {v} are completely connected, suggesting that one or more stops has found no '
                f'viable network nodes within the specified threshold')
            return None, None

    nodes_without_paths = graph_operations.extract_nodes_on_node_attributes(problem_g, conditions={'total_paths': 0})
    problem_g.remove_nodes_from(nodes_without_paths)

    problem_g.total_stops = schedule_g.number_of_nodes()
    if 'id' in schedule_element.__dict__:
        problem_g.id = schedule_element.id
    else:
        problem_g.id = 'schedule'

    return problem_g, schedule_g


def set_up_and_solve_model(g, solver='glpk'):
    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = ConcreteModel()  # noqa: F405

    # --------------------------------------------------------
    # Sets/Params
    # --------------------------------------------------------

    # nodes and edge sets
    # nodes: network's graph nodes that are closest to stops
    # edges: connections between nodes if they are in the same
    #    selection pool or there is no path between them
    vertices = g.nodes
    edges = g.edges

    model.vertices = Set(initialize=vertices)  # noqa: F405

    def spatial_proximity_coefficient_init(model, i):
        attribs = g.nodes[i]
        # todo normalise and invert
        return 1 / (attribs['total_path_lengths'] / attribs['total_paths'])
    model.c = Param(model.vertices, initialize=spatial_proximity_coefficient_init)  # noqa: F405

    # --------------------------------------------------------
    # Variables
    # --------------------------------------------------------

    model.x = Var(vertices, within=Binary)  # noqa: F405

    # --------------------------------------------------------
    # Constraints
    # --------------------------------------------------------

    model.edge_adjacency = ConstraintList()  # noqa: F405
    for u, v in edges:
        model.edge_adjacency.add(model.x[u] + model.x[v] <= 1)

    # --------------------------------------------------------
    # Objective
    # --------------------------------------------------------

    def total_nodes_rule(model):
        return sum(model.c[i] * model.x[i] for i in model.vertices)
    model.total_nodes = Objective(rule=total_nodes_rule, sense=maximize)  # noqa: F405

    # --------------------------------------------------------
    # Solver
    # --------------------------------------------------------

    logging.info('Passing problem to solver')
    _solver = SolverFactory(solver)  # noqa: F405
    _solver.solve(model)

    # --------------------------------------------------------
    # Solution parse
    # --------------------------------------------------------

    selected_nodes = [str(v).strip('x[]') for v in model.component_data_objects(Var) if  # noqa: F405
                      float(v.value) == 1.0]
    return {g.nodes[closest_node]['stop_id']: {'closest_node': closest_node.split('-')[0]}
            for closest_node in selected_nodes}
