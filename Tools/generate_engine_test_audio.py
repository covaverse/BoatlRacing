"""Generate original, low-level test audio for the long-tail engine prototype."""

from math import exp, pi, sin
from pathlib import Path
from random import Random
import struct
import wave


SAMPLE_RATE = 44_100
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "SourceAssets" / "Audio"


def write_pcm(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max(abs(sample) for sample in samples)
    if peak > 0.65:
        raise ValueError(f"Audio peak {peak:.3f} exceeds the test-asset limit")
    pcm = struct.pack(f"<{len(samples)}h", *(round(sample * 32767) for sample in samples))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)
    print(f"{path.name}: {len(samples) / SAMPLE_RATE:.2f}s, peak {peak:.3f}")


def engine_loop() -> list[float]:
    # All frequencies and amplitude modulations complete integer cycles in 4 s.
    count = SAMPLE_RATE * 4
    samples = []
    for index in range(count):
        t = index / SAMPLE_RATE
        pulse = 0.84 + 0.16 * sin(2 * pi * 8 * t)
        body = 0.15 * sin(2 * pi * 52 * t)
        exhaust = 0.07 * sin(2 * pi * 104 * t + 0.4)
        mechanical = 0.035 * sin(2 * pi * 156 * t + 1.0)
        samples.append(pulse * (body + exhaust + mechanical))
    return samples


def startup_cue() -> list[float]:
    duration = 1.7
    count = round(SAMPLE_RATE * duration)
    samples = []
    phase = 0.0
    for index in range(count):
        t = index / SAMPLE_RATE
        progress = t / duration
        frequency = 22 + 36 * progress * progress
        phase += 2 * pi * frequency / SAMPLE_RATE
        attack = min(1.0, t / 0.045)
        fade = min(1.0, (duration - t) / 0.26)
        crank = 0.11 * sin(phase) + 0.055 * sin(2 * phase + 0.3)
        pulse = 0.65 + 0.35 * sin(2 * pi * (5 + 3 * progress) * t)
        samples.append(attack * fade * pulse * crank)
    return samples


def lowpass_noise(count: int, alpha: float, seed: int) -> list[float]:
    rng = Random(seed)
    out, y = [], 0.0
    for _ in range(count):
        y += alpha * (rng.uniform(-1, 1) - y)
        out.append(y)
    return out


def seamless(samples: list[float], fade: int) -> list[float]:
    """Crossfade the tail into the head so the loop point has no click."""
    body = samples[:-fade]
    for i in range(fade):
        w = i / fade
        body[i] = body[i] * w + samples[len(samples) - fade + i] * (1 - w)
    return body


def normalise(samples: list[float], peak: float) -> list[float]:
    top = max(abs(s) for s in samples)
    return [s * peak / top for s in samples]


def water_loop() -> list[float]:
    # Hiss plus a slow slap rhythm; the Pawn raises pitch and volume with speed.
    count = SAMPLE_RATE * 4
    hiss = lowpass_noise(count + 4410, 0.25, 11)
    rumble = lowpass_noise(count + 4410, 0.02, 12)
    mixed = [0.5 * h + 2.5 * r for h, r in zip(hiss, rumble)]
    return normalise(seamless(mixed, 4410), 0.45)


def hull_hit() -> list[float]:
    duration = 0.6
    count = round(SAMPLE_RATE * duration)
    noise = lowpass_noise(count, 0.08, 21)
    samples = []
    for index in range(count):
        t = index / SAMPLE_RATE
        env = min(1.0, t / 0.004) * exp(-t * 9)
        thud = sin(2 * pi * (90 - 40 * t) * t)
        samples.append(env * (0.7 * thud + 0.6 * noise[index]))
    return normalise(samples, 0.6)


def canal_ambience() -> list[float]:
    # Soft breeze bed with sparse bird chirps; a stand-in for a recorded khlong ambience.
    count = SAMPLE_RATE * 8
    bed = lowpass_noise(count + 8820, 0.01, 31)
    samples = seamless([3.0 * b for b in bed], 8820)
    rng = Random(32)
    for _ in range(6):
        start = rng.randrange(0, count - SAMPLE_RATE)
        base = rng.uniform(2500, 4200)
        for index in range(round(SAMPLE_RATE * 0.12)):
            t = index / SAMPLE_RATE
            env = sin(pi * t / 0.12)
            samples[start + index] += 0.12 * env * sin(2 * pi * (base + 3000 * t) * t)
    return normalise(samples, 0.35)


def firing_loop(rpm: int, seed: int, pattern: tuple, pipe_hz: float, noise: float,
                peak: float) -> list[float]:
    """2 s seamless loop of 4-stroke 4-cylinder firing pulses at a fixed RPM.

    Firing rate is rpm/30 Hz, so rpm must be a multiple of 15 for a whole number of
    pulses in 2 s. Decay tails wrap around the loop point. Each pulse is a damped
    pipe resonance plus a noise bark; the uneven pattern gives the lumpy idle.
    """
    assert rpm % 15 == 0
    count = SAMPLE_RATE * 2
    pulses = rpm // 15
    out = [0.0] * count
    rng = Random(seed)
    decay = 60 + rpm / 40           # pulses get shorter and smoother as RPM rises
    pulse_len = round(SAMPLE_RATE * 6 / decay)
    for n in range(pulses):
        start = n * count // pulses + rng.randrange(-20, 21)
        gain = pattern[n % len(pattern)] * rng.uniform(0.85, 1.0)
        for i in range(pulse_len):
            t = i / SAMPLE_RATE
            env = exp(-t * decay)
            bark = (sin(2 * pi * pipe_hz * t) + 0.45 * sin(2 * pi * pipe_hz * 2.3 * t)
                    + noise * rng.uniform(-1, 1))
            out[(start + i) % count] += gain * env * bark
    return normalise(out, peak)


# RPMs the band loops are "recorded" at; the Pawn's EngineIdleRPM..EngineHighRPM defaults match.
ENGINE_BANDS = (("idle", 900, 0.6), ("low", 2400, 0.4), ("mid", 3900, 0.3), ("high", 5400, 0.25))


def engine_band(rpm: int, noise: float) -> list[float]:
    return firing_loop(rpm, 60 + rpm // 100, (1.0, 0.7, 0.9, 0.6), 140 + rpm / 25, noise, 0.4)


def exhaust_loop() -> list[float]:
    # Straight-pipe bark recorded at 3000 RPM (ExhaustLoopRPM): louder, rougher, more noise.
    return firing_loop(3000, 41, (1.0, 0.55, 0.85, 0.45), 190, 0.7, 0.5)


def exhaust_pops() -> list[float]:
    # Lift-off crackle: a few sharp bangs with a low thump, spread over half a second.
    duration = 0.7
    count = round(SAMPLE_RATE * duration)
    out = [0.0] * count
    rng = Random(51)
    for start_s, gain in ((0.0, 1.0), (0.09, 0.6), (0.21, 0.85), (0.3, 0.4), (0.44, 0.55)):
        start = round(start_s * SAMPLE_RATE)
        for i in range(round(SAMPLE_RATE * 0.08)):
            t = i / SAMPLE_RATE
            crack = exp(-t * 90) * rng.uniform(-1, 1)
            thump = exp(-t * 35) * sin(2 * pi * 70 * t)
            out[start + i] += gain * (0.8 * crack + 0.7 * thump)
    return normalise(out, 0.6)


if __name__ == "__main__":
    write_pcm(OUTPUT_DIR / "longtail_engine_test.wav", engine_loop())
    write_pcm(OUTPUT_DIR / "longtail_start_test.wav", startup_cue())
    write_pcm(OUTPUT_DIR / "longtail_water_test.wav", water_loop())
    write_pcm(OUTPUT_DIR / "longtail_hit_test.wav", hull_hit())
    write_pcm(OUTPUT_DIR / "canal_ambience_test.wav", canal_ambience())
    write_pcm(OUTPUT_DIR / "longtail_exhaust_test.wav", exhaust_loop())
    for name, rpm, noise in ENGINE_BANDS:
        write_pcm(OUTPUT_DIR / f"longtail_engine_{name}_test.wav", engine_band(rpm, noise))
    write_pcm(OUTPUT_DIR / "longtail_exhaust_pop_test.wav", exhaust_pops())
