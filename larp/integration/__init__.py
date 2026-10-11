"""Versioned adapters between the evidence, strategy/risk and runtime components (IDEA-031 stage 3).

Nothing here creates trading authority. Every adapter either converts a producer's record into the
consumer's documented contract or returns a typed rejection; nothing is silently dropped.
"""
