# EdgeCloudContinuum Gem (draft)

**Status: written following O3DE conventions, never compiled.**

The sources and build files here were written without an O3DE installation,
so nothing has been built or loaded in the Editor yet. Details such as the
`AZ_CLASS_ALLOCATOR` signature and CMake helpers depend on the O3DE version
and may need small fixes on first build.

To validate on a machine that can run O3DE:

1. Register the gem: `o3de register --gem-path ./Gem`
2. Add `EdgeCloudContinuum` to a project and build it.
3. Check that the "Cognitive Agent" component appears in the Editor.

If the build fails, a reliable fallback is to generate a fresh gem skeleton with
`o3de create-gem` and copy `Include/` and `Source/` into it.
