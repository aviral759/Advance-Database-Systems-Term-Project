"""OpenCLIP joint image-text embeddings + CLIP zero-shot auto-tagging."""
from __future__ import annotations

import hashlib
import logging
from typing import Protocol, Sequence

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


class Embedder(Protocol):
    model_id: str
    dim: int
    device: str

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray: ...
    def encode_texts(self, texts: Sequence[str]) -> np.ndarray: ...


def l2_normalize(x) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = x[None, :]
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return np.ascontiguousarray(x / norms, dtype=np.float32)


class OpenClipEmbedder:
    def __init__(self, model_name: str, pretrained: str, device: str = "auto", batch_size: int = 32):
        import open_clip
        import torch

        self._torch = torch
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.batch_size = batch_size
        log.info("Loading OpenCLIP %s (%s) on %s", model_name, pretrained, device)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=device
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(model_name)
        self.model_id = f"openclip:{model_name}:{pretrained}"
        self.dim = 0
        self.dim = int(self.encode_texts(["warm-up"]).shape[1])

    def encode_images(self, images: Sequence[Image.Image]) -> np.ndarray:
        torch = self._torch
        chunks = []
        for i in range(0, len(images), self.batch_size):
            batch = torch.stack([self.preprocess(im.convert("RGB")) for im in images[i:i + self.batch_size]])
            with torch.inference_mode():
                feats = self.model.encode_image(batch.to(self.device))
            chunks.append(feats.float().cpu().numpy())
        return l2_normalize(np.concatenate(chunks)) if chunks else np.zeros((0, self.dim), np.float32)

    def encode_texts(self, texts: Sequence[str]) -> np.ndarray:
        torch = self._torch
        chunks = []
        for i in range(0, len(texts), 256):
            tokens = self.tokenizer(list(texts[i:i + 256])).to(self.device)
            with torch.inference_mode():
                feats = self.model.encode_text(tokens)
            chunks.append(feats.float().cpu().numpy())
        return l2_normalize(np.concatenate(chunks)) if chunks else np.zeros((0, self.dim), np.float32)


class FakeEmbedder:
    """Deterministic hash-based vectors. Used for tests/CI (HPS_FAKE_EMBEDDER=1); no model download."""
    model_id = "fake:hash64"
    dim = 64
    device = "cpu"

    def _vec(self, key: bytes) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "little")
        return np.random.default_rng(seed).standard_normal(self.dim)

    def encode_images(self, images):
        if not images:
            return np.zeros((0, self.dim), np.float32)
        return l2_normalize([self._vec(im.convert("RGB").resize((8, 8)).tobytes()) for im in images])

    def encode_texts(self, texts):
        if not texts:
            return np.zeros((0, self.dim), np.float32)
        return l2_normalize([self._vec(t.lower().encode()) for t in texts])


def build_embedder(settings) -> Embedder:
    if settings.fake_embedder:
        log.warning("Using FakeEmbedder: semantic results are NOT meaningful (test mode).")
        return FakeEmbedder()
    return OpenClipEmbedder(settings.model_name, settings.pretrained, settings.device)


COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog",
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich",
    "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book",
    "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
]
SCENES = [
    "beach", "mountain", "forest", "city street", "snow", "night", "sunset", "kitchen",
    "living room", "bedroom", "bathroom", "office", "park", "ocean", "desert", "river",
    "field", "sky", "building", "crowd", "airport", "stadium", "road", "garden",
]


class ZeroShotTagger:
    """Tags images by CLIP similarity to prompt embeddings of a fixed vocabulary."""

    def __init__(self, embedder: Embedder, vocab: Sequence[str] | None = None,
                 top_k: int = 5, min_prob: float = 0.08):
        self.vocab = list(vocab or COCO_CLASSES + SCENES)
        self.top_k, self.min_prob = top_k, min_prob
        self.text_emb = embedder.encode_texts([f"a photo of a {v}." for v in self.vocab])

    def tag(self, image_embs: np.ndarray) -> list[list[tuple[str, float]]]:
        if len(image_embs) == 0:
            return []
        logits = 100.0 * (image_embs @ self.text_emb.T)
        logits -= logits.max(axis=1, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=1, keepdims=True)
        out = []
        for row in probs:
            idx = np.argsort(-row)[: self.top_k]
            out.append([(self.vocab[i], float(row[i])) for i in idx if row[i] >= self.min_prob])
        return out