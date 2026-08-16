cmake_minimum_required(VERSION 3.0.2)
project(car3)

find_package(catkin REQUIRED)
catkin_package()

catkin_install_python(PROGRAMS
  scripts/generate_scaled_urdf.py
  scripts/initialize_car3.py
  scripts/gripper_mimic.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

if(CATKIN_ENABLE_TESTING)
  find_package(PythonInterp REQUIRED)
  add_test(NAME car3_initialization_contract
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/test/test_initialization_contract.py)
  add_test(NAME car3_scaled_urdf_contract
    COMMAND ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/test/test_scaled_urdf.py)
endif()

install(DIRECTORY config meshes urdf
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
