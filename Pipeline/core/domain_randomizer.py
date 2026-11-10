"""Domain randomization for physics, environment and camera parameters.

Samples scenario parameters from the ranges defined in config.json. The output
is plain JSON-serializable data that a simulator (for example the O3DE Gem in
Gem/) can consume to configure PhysX bodies, Atom environment settings and the
camera. Sampling is seeded, so every scenario is reproducible.
"""
import random


def _uniform(rng, bounds):
    low, high = bounds
    return rng.uniform(low, high)


def sample_physics(rng, cfg):
    return {
        "mass_kg": round(_uniform(rng, cfg["mass_kg"]), 3),
        "friction": round(_uniform(rng, cfg["friction"]), 3),
        "restitution": round(_uniform(rng, cfg["restitution"]), 3),
    }


def sample_environment(rng, cfg):
    return {
        "fog_density": round(_uniform(rng, cfg["fog_density"]), 4),
        "sun_azimuth_deg": round(_uniform(rng, cfg["sun_azimuth_deg"]), 2),
        "pbr_roughness": round(_uniform(rng, cfg["pbr_roughness"]), 3),
    }


def sample_camera(rng, cfg):
    x, y, z = (round(_uniform(rng, axis), 3) for axis in cfg["position_m"])
    return {
        "position_m": [x, y, z],
        "yaw_deg": round(_uniform(rng, cfg["yaw_deg"]), 2),
        "pitch_deg": round(_uniform(rng, cfg["pitch_deg"]), 2),
        "fov_deg": round(_uniform(rng, cfg["fov_deg"]), 2),
    }


def generate_episode(config, episode_id, base_seed=0):
    """Build one episode: physics sampled once, environment and camera per frame."""
    rng = random.Random(base_seed * 1_000_003 + episode_id)
    frames = [
        {
            "frame": i,
            "environment": sample_environment(rng, config["environment"]),
            "camera": sample_camera(rng, config["camera"]),
        }
        for i in range(config["frames_per_episode"])
    ]
    return {
        "episode_id": episode_id,
        "seed": base_seed,
        "physics": sample_physics(rng, config["physics"]),
        "frames": frames,
    }
