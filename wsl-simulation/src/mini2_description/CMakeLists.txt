cmake_minimum_required(VERSION 3.0.2)

project(mini2_description)

find_package(catkin REQUIRED)
find_package(PythonInterp REQUIRED)

catkin_package()

find_package(roslaunch REQUIRED)

catkin_install_python(PROGRAMS
  scripts/check_mini2_sensors.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

foreach(dir config launch meshes urdf)
	install(DIRECTORY ${dir}/
		DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/${dir})
endforeach(dir)

if(CATKIN_ENABLE_TESTING)
  catkin_add_nosetests(test/test_sim_urdf.py)
endif()
