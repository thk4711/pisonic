"""External display artwork is bounded before native pixel decoding."""

import threading
from unittest import mock

import pytest
from display import display_rendering as rendering
from online_artwork import CoverArtArchiveClient
from PIL import Image


def _renderer(path):
    renderer = rendering.DisplayRenderingMixin()
    renderer._state_lock = threading.Lock()
    renderer.metadata = {"cover": str(path), "md5": "cover", "art_mode": "cover"}
    return renderer


@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_display_accepts_bounded_supported_artwork(tmp_path, fmt):
    path = tmp_path / "cover.image"
    Image.new("RGB", (12, 8)).save(path, format=fmt)
    image, *_ = _renderer(path)._open_cover()
    assert image.mode == "RGBA"
    assert image.size == (12, 8)


@pytest.mark.parametrize("fmt", ["GIF", "TIFF", "BMP"])
def test_display_rejects_other_decoders_despite_jpeg_filename(tmp_path, fmt):
    path = tmp_path / "cover.jpg"
    Image.new("RGB", (12, 8)).save(path, format=fmt)
    assert _renderer(path)._open_cover()[0] is None


def test_display_rejects_file_size_before_opening_decoder(tmp_path, monkeypatch):
    path = tmp_path / "cover.jpg"
    path.write_bytes(b"oversized")
    monkeypatch.setattr(rendering, "MAX_COVER_BYTES", 4)
    monkeypatch.setattr(Image, "open", lambda *a, **k: pytest.fail("decoder opened"))
    assert _renderer(path)._open_cover()[0] is None


def test_display_rejects_dimensions_before_conversion(tmp_path, monkeypatch):
    path = tmp_path / "cover.png"
    Image.new("RGB", (20, 1)).save(path)
    monkeypatch.setattr(rendering, "MAX_COVER_DIMENSION", 10)
    monkeypatch.setattr(Image.Image, "convert", lambda *a, **k: pytest.fail("pixels decoded"))
    assert _renderer(path)._open_cover()[0] is None


@pytest.mark.parametrize("size", [(4, 4), (8, 8)])
def test_display_rejects_decompression_bomb_warning_and_error(tmp_path, monkeypatch, size):
    path = tmp_path / "cover.png"
    Image.new("RGB", size).save(path)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
    assert _renderer(path)._open_cover()[0] is None


def test_online_normalizer_limits_decoders_before_opening(monkeypatch):
    opened = mock.Mock(side_effect=OSError("invalid image"))
    monkeypatch.setattr(Image, "open", opened)
    assert CoverArtArchiveClient._normalize_image(b"invalid") is None
    assert opened.call_args.kwargs["formats"] == ("PNG", "JPEG")
