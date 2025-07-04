cmake_minimum_required(VERSION 3.29)
project(cliente_sensor_cpp)

set(CMAKE_CXX_STANDARD 20)

add_executable(cliente_sensor_cpp main.cpp main.cpp)

if(WIN32)
    target_compile_definitions(cliente_sensor_cpp PRIVATE _WIN32_WINNT=0x0601)
    target_link_libraries(cliente_sensor_cpp ws2_32)
endif()

find_package(OpenSSL REQUIRED)
if( OPENSSL_FOUND )
    include_directories(${OPENSSL_INCLUDE_DIR})
    link_directories(${OPENSSL_LIBRARIES})
    message(STATUS "Usando OpenSSL ${OPENSSL_VERSION}")
    message(STATUS "OpenSSL include dir: ${OPENSSL_INCLUDE_DIR}")
    target_link_libraries(${PROJECT_NAME} OpenSSL::SSL OpenSSL::Crypto)
endif()

# openssl
