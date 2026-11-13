# Static library with the gem's code, shared by every target below.
ly_add_target(
    NAME EdgeCloudContinuum.Static STATIC
    NAMESPACE Gem
    FILES_CMAKE
        edgecloudcontinuum_files.cmake
    INCLUDE_DIRECTORIES
        PUBLIC
            Include
        PRIVATE
            Source
    BUILD_DEPENDENCIES
        PUBLIC
            AZ::AzCore
            AZ::AzFramework
)

# Runtime module that the engine loads.
ly_add_target(
    NAME EdgeCloudContinuum ${PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE}
    NAMESPACE Gem
    FILES_CMAKE
        edgecloudcontinuum_shared_files.cmake
    INCLUDE_DIRECTORIES
        PUBLIC
            Include
        PRIVATE
            Source
    BUILD_DEPENDENCIES
        PRIVATE
            Gem::EdgeCloudContinuum.Static
)

# Clients and servers load the same module.
ly_create_alias(NAME EdgeCloudContinuum.Clients NAMESPACE Gem TARGETS Gem::EdgeCloudContinuum)
ly_create_alias(NAME EdgeCloudContinuum.Servers NAMESPACE Gem TARGETS Gem::EdgeCloudContinuum)
