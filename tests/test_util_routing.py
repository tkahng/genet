import pytest
from genet.utils import routing
import genet.utils.spatial as spatial
from tests.fixtures import assert_semantically_equal
from tests.test_modify_schedule import network


def test_showing_unique_network_schedule_modes(network):
    assert network.schedule_modes() == {'rail', 'bus'}


def test_build_graph_for_maximum_stable_set_problem_with_non_trivial_closest_node_selection_pool(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_4', 'node_5', 'node_6'], ['node_7', 'node_8', 'node_9'],
                                     ['node_1', 'node_2', 'node_3']])
    network.schedule.id = 'id'
    problem_g, schedule_g = routing.build_graph_for_maximum_stable_set_problem(network.graph, network.schedule, 1)
    assert_semantically_equal(dict(schedule_g.nodes(data=True)),
                              {'stop_2': {'x': 2.0, 'y': 2.5, 'lat': 49.76683094462549, 'lon': -7.557134732217642,
                                          's2_id': 5205973754090230267,
                                          'closest_nodes': ['node_4-stop_2', 'node_5-stop_2', 'node_6-stop_2']},
                               'stop_3': {'x': 5.5, 'y': 2.0, 'lat': 49.76682879603468, 'lon': -7.55708584676138,
                                          's2_id': 5205973754096513977,
                                          'closest_nodes': ['node_7-stop_3', 'node_8-stop_3', 'node_9-stop_3']},
                               'stop_1': {'x': 1.0, 'y': 2.5, 'lat': 49.76683027967191, 'lon': -7.557148552832129,
                                          's2_id': 5205973754090340691,
                                          'closest_nodes': ['node_1-stop_1', 'node_2-stop_1', 'node_3-stop_1']}})
    assert_semantically_equal(list(schedule_g.edges()), [('stop_2', 'stop_3'), ('stop_1', 'stop_2')])
    assert_semantically_equal(dict(problem_g.nodes(data=True)),
                              {'node_4-stop_2': {'total_path_lengths': 16, 'total_paths': 6, 'stop_id': 'stop_2'},
                               'node_5-stop_2': {'total_path_lengths': 16, 'total_paths': 6, 'stop_id': 'stop_2'},
                               'node_6-stop_2': {'total_path_lengths': 16, 'total_paths': 6, 'stop_id': 'stop_2'},
                               'node_7-stop_3': {'total_path_lengths': 6, 'total_paths': 3, 'stop_id': 'stop_3'},
                               'node_8-stop_3': {'total_path_lengths': 9, 'total_paths': 3, 'stop_id': 'stop_3'},
                               'node_9-stop_3': {'total_path_lengths': 12, 'total_paths': 3, 'stop_id': 'stop_3'},
                               'node_1-stop_1': {'total_path_lengths': 6, 'total_paths': 3, 'stop_id': 'stop_1'},
                               'node_2-stop_1': {'total_path_lengths': 9, 'total_paths': 3, 'stop_id': 'stop_1'},
                               'node_3-stop_1': {'total_path_lengths': 6, 'total_paths': 3, 'stop_id': 'stop_1'}})
    assert_semantically_equal(list(problem_g.edges()),
                              [('node_4-stop_2', 'node_5-stop_2'), ('node_4-stop_2', 'node_6-stop_2'),
                               ('node_5-stop_2', 'node_6-stop_2'), ('node_7-stop_3', 'node_8-stop_3'),
                               ('node_7-stop_3', 'node_9-stop_3'), ('node_8-stop_3', 'node_9-stop_3'),
                               ('node_1-stop_1', 'node_2-stop_1'), ('node_1-stop_1', 'node_3-stop_1'),
                               ('node_2-stop_1', 'node_3-stop_1')]
                              )


def test_build_graph_for_maximum_stable_set_problem_with_no_path_between_isolated_node(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['isolated_node', 'node_5', 'node_6'], ['node_7', 'node_8'], ['node_1', 'node_2']])
    network.add_node('isolated_node', x_y=(0,0))
    problem_g, schedule_g = routing.build_graph_for_maximum_stable_set_problem(network.graph, network.schedule, 1)
    assert_semantically_equal(dict(schedule_g.nodes(data=True)),
                              {'stop_2': {'x': 2.0, 'y': 2.5, 'lat': 49.76683094462549, 'lon': -7.557134732217642,
                                          's2_id': 5205973754090230267,
                                          'closest_nodes': ['isolated_node-stop_2', 'node_5-stop_2', 'node_6-stop_2']},
                               'stop_3': {'x': 5.5, 'y': 2.0, 'lat': 49.76682879603468, 'lon': -7.55708584676138,
                                          's2_id': 5205973754096513977,
                                          'closest_nodes': ['node_7-stop_3', 'node_8-stop_3']},
                               'stop_1': {'x': 1.0, 'y': 2.5, 'lat': 49.76683027967191, 'lon': -7.557148552832129,
                                          's2_id': 5205973754090340691,
                                          'closest_nodes': ['node_1-stop_1', 'node_2-stop_1']}})
    assert_semantically_equal(list(schedule_g.edges()), [('stop_2', 'stop_3'), ('stop_1', 'stop_2')])
    assert_semantically_equal(dict(problem_g.nodes(data=True)),
                              {'isolated_node-stop_2': {'total_path_lengths': 0, 'total_paths': 0, 'stop_id': 'stop_2'},
                               'node_5-stop_2': {'total_path_lengths': 10, 'total_paths': 4, 'stop_id': 'stop_2'},
                               'node_6-stop_2': {'total_path_lengths': 10, 'total_paths': 4, 'stop_id': 'stop_2'},
                               'node_7-stop_3': {'total_path_lengths': 3, 'total_paths': 2, 'stop_id': 'stop_3'},
                               'node_8-stop_3': {'total_path_lengths': 5, 'total_paths': 2, 'stop_id': 'stop_3'},
                               'node_1-stop_1': {'total_path_lengths': 5, 'total_paths': 2, 'stop_id': 'stop_1'},
                               'node_2-stop_1': {'total_path_lengths': 7, 'total_paths': 2, 'stop_id': 'stop_1'}})
    assert_semantically_equal(list(problem_g.edges()),
                              [('isolated_node-stop_2', 'node_5-stop_2'), ('isolated_node-stop_2', 'node_6-stop_2'),
                               ('isolated_node-stop_2', 'node_7-stop_3'), ('isolated_node-stop_2', 'node_8-stop_3'),
                               ('node_5-stop_2', 'node_6-stop_2'), ('node_7-stop_3', 'node_8-stop_3'),
                               ('node_1-stop_1', 'node_2-stop_1'), ('node_1-stop_1', 'isolated_node-stop_2'),
                               ('node_2-stop_1', 'isolated_node-stop_2')]
                              )


def test_routing_single_route(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_1', 'node_2'], ['node_5', 'node_6']])
    pass
