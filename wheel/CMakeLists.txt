cmake_minimum_required(VERSION 3.16)
project(graphite-workspace-scroll VERSION 1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Quick DBus)
find_package(KF6CoreAddons REQUIRED)
find_package(KF6Config REQUIRED)
# The effect needs KWin's installed headers and library, not its full build
# dependency graph (ECM, Vulkan, Wayland scanner, etc.). No downloads occur.
find_path(KWIN_INCLUDE_DIR effect/effect.h PATH_SUFFIXES kwin REQUIRED)
find_library(KWIN_LIBRARY NAMES kwin REQUIRED)
list(APPEND CMAKE_AUTOMOC_MACRO_NAMES KWIN_EFFECT_FACTORY_SUPPORTED)
add_library(kwin_hypr_scroll_desktop MODULE
    src/workspace-scroll.cpp src/workspace-scroll.h src/plugin.cpp)
set_target_properties(kwin_hypr_scroll_desktop PROPERTIES PREFIX "")
target_include_directories(kwin_hypr_scroll_desktop PRIVATE ${KWIN_INCLUDE_DIR})
target_link_libraries(kwin_hypr_scroll_desktop PRIVATE ${KWIN_LIBRARY}
    Qt6::Core Qt6::Gui Qt6::Widgets Qt6::Quick Qt6::DBus
    KF6::CoreAddons KF6::ConfigCore)
set(GRAPHITE_PLUGIN_DIR "lib/qt6/plugins" CACHE STRING "Qt plugin directory relative to install prefix")
install(TARGETS kwin_hypr_scroll_desktop
    LIBRARY DESTINATION "${GRAPHITE_PLUGIN_DIR}/kwin/effects/plugins")
