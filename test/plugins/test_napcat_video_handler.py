from __future__ import annotations

from plugins.napcat_adapter.src.handlers.video_handler import VideoDownloader


def test_video_downloader_default_size_limit_is_200mb() -> None:
    downloader = VideoDownloader()

    assert downloader.max_size_mb == 200


def test_video_downloader_size_limit_boundary() -> None:
    downloader = VideoDownloader(max_size_mb=200)

    assert downloader.check_file_size(str(200 * 1024 * 1024))
    assert not downloader.check_file_size(str(201 * 1024 * 1024))
