cmake_minimum_required(VERSION 3.0.2)
project(robot_dog_lidar)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  sensor_msgs
)
find_package(Threads REQUIRED)

set(YDLIDAR_SDK_SOURCE "/opt/ydlidar-sdk-src" CACHE PATH
  "Mounted path to the vendor YDLIDAR SDK source")

if(NOT EXISTS "${YDLIDAR_SDK_SOURCE}/CMakeLists.txt")
  message(FATAL_ERROR
    "YDLIDAR SDK source not found at ${YDLIDAR_SDK_SOURCE}. "
    "Mount the confirmed vendor SDK there before building robot_dog_lidar.")
endif()

set(YDLIDAR_SDK_VERSION "1.2.17")
configure_file(
  "${YDLIDAR_SDK_SOURCE}/ydlidar_config.h.in"
  "${CMAKE_CURRENT_BINARY_DIR}/ydlidar_config.h"
  @ONLY
)

file(GLOB_RECURSE YDLIDAR_VENDOR_SOURCES
  "${YDLIDAR_SDK_SOURCE}/core/*.c"
  "${YDLIDAR_SDK_SOURCE}/core/*.cpp"
  "${YDLIDAR_SDK_SOURCE}/src/*.cpp"
)

set(YDLIDAR_UNIX_SOURCES)
foreach(source_file IN LISTS YDLIDAR_VENDOR_SOURCES)
  if(NOT source_file MATCHES "/impl/windows/")
    list(APPEND YDLIDAR_UNIX_SOURCES "${source_file}")
  endif()
endforeach()

if(NOT YDLIDAR_UNIX_SOURCES)
  message(FATAL_ERROR "No usable YDLIDAR SDK sources were found.")
endif()

add_library(ydlidar_sdk_vendor STATIC ${YDLIDAR_UNIX_SOURCES})
target_compile_features(ydlidar_sdk_vendor PUBLIC cxx_std_14)
target_include_directories(ydlidar_sdk_vendor PUBLIC
  "${CMAKE_CURRENT_BINARY_DIR}"
  "${YDLIDAR_SDK_SOURCE}"
  "${YDLIDAR_SDK_SOURCE}/core"
  "${YDLIDAR_SDK_SOURCE}/src"
)
target_link_libraries(ydlidar_sdk_vendor PUBLIC Threads::Threads)

catkin_package(CATKIN_DEPENDS roscpp sensor_msgs)

add_executable(ydlidar_scan_node src/ydlidar_scan_node.cpp)
target_compile_features(ydlidar_scan_node PUBLIC cxx_std_14)
target_link_libraries(ydlidar_scan_node
  ydlidar_sdk_vendor
  ${catkin_LIBRARIES}
)
target_include_directories(ydlidar_scan_node PRIVATE
  ${catkin_INCLUDE_DIRS}
  "${CMAKE_CURRENT_BINARY_DIR}"
  "${YDLIDAR_SDK_SOURCE}"
  "${YDLIDAR_SDK_SOURCE}/core"
  "${YDLIDAR_SDK_SOURCE}/src"
)

install(TARGETS ydlidar_scan_node
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)
