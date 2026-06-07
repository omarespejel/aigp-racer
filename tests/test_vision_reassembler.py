from __future__ import annotations

import pytest

from vision.reassembler import (
    HEADER_SIZE,
    JpegFrameReassembler,
    VisionChunkHeader,
    VisionPacketError,
    pack_header,
    parse_datagram,
)


def chunk_datagram(
    *,
    frame_id: int,
    chunk_id: int,
    total_chunks: int,
    jpeg_size: int,
    payload: bytes,
    sim_time_ns: int = 123_456,
) -> bytes:
    header = VisionChunkHeader(
        frame_id=frame_id,
        chunk_id=chunk_id,
        total_chunks=total_chunks,
        jpeg_size=jpeg_size,
        payload_size=len(payload),
        sim_time_ns=sim_time_ns,
    )
    return pack_header(header) + payload


def test_header_size_matches_spec() -> None:
    assert HEADER_SIZE == 24


def test_parse_datagram_preserves_header_and_payload() -> None:
    datagram = chunk_datagram(
        frame_id=7,
        chunk_id=0,
        total_chunks=1,
        jpeg_size=4,
        payload=b"\xff\xd8xx",
        sim_time_ns=42,
    )

    chunk = parse_datagram(datagram)

    assert chunk.header.frame_id == 7
    assert chunk.header.sim_time_ns == 42
    assert chunk.payload == b"\xff\xd8xx"


def test_reassembles_out_of_order_chunks() -> None:
    reassembler = JpegFrameReassembler()
    jpeg = b"\xff\xd8abcdef\xff\xd9"
    first = chunk_datagram(
        frame_id=1,
        chunk_id=0,
        total_chunks=2,
        jpeg_size=len(jpeg),
        payload=jpeg[:5],
    )
    second = chunk_datagram(
        frame_id=1,
        chunk_id=1,
        total_chunks=2,
        jpeg_size=len(jpeg),
        payload=jpeg[5:],
    )

    assert reassembler.add_datagram(second) is None
    frame = reassembler.add_datagram(first)

    assert frame is not None
    assert frame.jpeg == jpeg
    assert frame.frame_id == 1
    assert frame.chunk_count == 2
    assert frame.sim_time_ns == 123_456


def test_missing_chunk_keeps_partial_frame() -> None:
    reassembler = JpegFrameReassembler()
    datagram = chunk_datagram(
        frame_id=3,
        chunk_id=0,
        total_chunks=2,
        jpeg_size=10,
        payload=b"first",
    )

    assert reassembler.add_datagram(datagram) is None
    assert reassembler.partial_frame_count == 1


def test_duplicate_identical_chunk_is_ignored() -> None:
    reassembler = JpegFrameReassembler()
    datagram = chunk_datagram(
        frame_id=4,
        chunk_id=0,
        total_chunks=2,
        jpeg_size=6,
        payload=b"abc",
    )

    assert reassembler.add_datagram(datagram) is None
    assert reassembler.add_datagram(datagram) is None
    assert reassembler.partial_frame_count == 1


def test_duplicate_conflicting_chunk_is_rejected() -> None:
    reassembler = JpegFrameReassembler()
    first = chunk_datagram(frame_id=4, chunk_id=0, total_chunks=2, jpeg_size=6, payload=b"abc")
    second = chunk_datagram(frame_id=4, chunk_id=0, total_chunks=2, jpeg_size=6, payload=b"xyz")

    assert reassembler.add_datagram(first) is None
    with pytest.raises(VisionPacketError, match="duplicate chunk_id"):
        reassembler.add_datagram(second)


def test_rejects_short_header() -> None:
    with pytest.raises(VisionPacketError, match="shorter"):
        parse_datagram(b"x" * 23)


def test_rejects_payload_size_mismatch() -> None:
    header = VisionChunkHeader(
        frame_id=1,
        chunk_id=0,
        total_chunks=1,
        jpeg_size=4,
        payload_size=99,
        sim_time_ns=1,
    )

    with pytest.raises(VisionPacketError, match="payload_size"):
        parse_datagram(pack_header(header) + b"abcd")


def test_rejects_chunk_index_out_of_range() -> None:
    datagram = chunk_datagram(frame_id=1, chunk_id=2, total_chunks=2, jpeg_size=4, payload=b"ab")

    with pytest.raises(VisionPacketError, match="chunk_id"):
        parse_datagram(datagram)


def test_drops_oldest_partial_frame_when_capacity_exceeded() -> None:
    reassembler = JpegFrameReassembler(max_partial_frames=1)
    first = chunk_datagram(frame_id=1, chunk_id=0, total_chunks=2, jpeg_size=4, payload=b"aa")
    second = chunk_datagram(frame_id=2, chunk_id=0, total_chunks=2, jpeg_size=4, payload=b"bb")

    assert reassembler.add_datagram(first) is None
    assert reassembler.add_datagram(second) is None

    assert reassembler.partial_frame_count == 1
    assert reassembler.dropped_partial_frames == 1
