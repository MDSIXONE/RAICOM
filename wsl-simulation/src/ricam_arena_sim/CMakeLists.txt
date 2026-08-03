cmake_minimum_required(VERSION 3.0.2)
project(ricam_arena_sim)

find_package(catkin REQUIRED)
catkin_package()

install(DIRECTORY config launch maps meshes rviz worlds
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

catkin_install_python(PROGRAMS
  scripts/arena_geometry.py
  scripts/generate_arena_blend.py
  scripts/generate_numbered_grid.py
  scripts/generate_rviz_map.py
  scripts/navigate_numbered_waypoints.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

if(CATKIN_ENABLE_TESTING)
  catkin_add_nosetests(test/test_recognition_geometry.py)
  catkin_add_nosetests(test/test_navigation_contract.py)
  catkin_add_nosetests(test/test_numbered_grid.py)
  catkin_add_nosetests(test/test_waypoint_route.py)
endif()
