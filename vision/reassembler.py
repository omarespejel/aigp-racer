"""Chunked JPEG frame reassembly for the AI Grand Prix vision stream."""

from __future__ import annotations

import struct
from collections import OrderedDict
from dataclasses import dataclass, field

HEADER_STRUCT = struct.Struct("<IHHIIQ")
HEADER_SIZE = HEADER_STRUCT.size
DEFAULT_MAX_PARTIAL_FRAMES = 8


class VisionPacketError(ValueError):
    """Raised when a vision UDP datagram violates the expected packet contract."""


@dataclass(frozen=True)
class VisionChunkHeader:
    """AI Grand Prix vision-packet header."""

    frame_id: int
    chunk_id: int
    total_chunks: int
    jpeg_size: int
    payload_size: int
    sim_time_ns: int


@dataclass(frozen=True)
class VisionChunk:
    """Parsed vision datagram."""

    header: VisionChunkHeader
    payload: bytes


@dataclass(frozen=True)
class ReassembledFrame:
    """Complete JPEG frame reconstructed from one or more UDP chunks."""

    frame_id: int
    sim_time_ns: int
    jpeg: bytes
    chunk_count: int


@dataclass
class _PartialFrame:
    frame_id: int
    total_chunks: int
    jpeg_size: int
    sim_time_ns: int
    chunks: dict[int, bytes] = field(default_factory=dict)

    def add(self, chunk: VisionChunk) -> None:
        header = chunk.header
        if header.total_chunks != self.total_chunks:
            raise VisionPacketError("conflicting total_chunks for frame")
        if header.jpeg_size != self.jpeg_size:
            raise VisionPacketError("conflicting jpeg_size for frame")
        if header.sim_time_ns != self.sim_time_ns:
            raise VisionPacketError("conflicting sim_time_ns for frame")

        existing = self.chunks.get(header.chunk_id)
        if existing is not None:
            if existing != chunk.payload:
                raise VisionPacketError("duplicate chunk_id with different payload")
            return
        self.chunks[header.chunk_id] = chunk.payload

    @property
    def complete(self) -> bool:
        return len(self.chunks) == self.total_chunks

    def assemble(self) -> ReassembledFrame:
        if not self.complete:
            raise VisionPacketError("cannot assemble incomplete frame")
        jpeg = b"".join(self.chunks[index] for index in range(self.total_chunks))
        if len(jpeg) != self.jpeg_size:
            raise VisionPacketError(
                f"assembled JPEG size {len(jpeg)} does not match header {self.jpeg_size}"
            )
        return ReassembledFrame(
            frame_id=self.frame_id,
            sim_time_ns=self.sim_time_ns,
            jpeg=jpeg,
            chunk_count=self.total_chunks,
        )


def pack_header(header: VisionChunkHeader) -> bytes:
    """Pack a header for tests and local fixtures."""

    return HEADER_STRUCT.pack(
        header.frame_id,
        header.chunk_id,
        header.total_chunks,
        header.jpeg_size,
        header.payload_size,
        header.sim_time_ns,
    )


def parse_datagram(datagram: bytes) -> VisionChunk:
    """Parse one UDP datagram into a typed vision chunk."""

    if len(datagram) < HEADER_SIZE:
        raise VisionPacketError("vision datagram shorter than 24-byte header")

    values = HEADER_STRUCT.unpack(datagram[:HEADER_SIZE])
    header = VisionChunkHeader(*values)
    payload = datagram[HEADER_SIZE:]

    if header.total_chunks <= 0:
        raise VisionPacketError("total_chunks must be positive")
    if header.chunk_id >= header.total_chunks:
        raise VisionPacketError("chunk_id must be within total_chunks")
    if header.jpeg_size <= 0:
        raise VisionPacketError("jpeg_size must be positive")
    if header.payload_size != len(payload):
        raise VisionPacketError("payload_size does not match datagram payload")
    if header.payload_size > header.jpeg_size:
        raise VisionPacketError("payload_size cannot exceed jpeg_size")

    return VisionChunk(header=header, payload=payload)


class JpegFrameReassembler:
    """Bounded reassembler for the official chunked JPEG UDP stream."""

    def __init__(self, max_partial_frames: int = DEFAULT_MAX_PARTIAL_FRAMES) -> None:
        if max_partial_frames <= 0:
            raise ValueError("max_partial_frames must be positive")
        self.max_partial_frames = max_partial_frames
        self._partials: OrderedDict[int, _PartialFrame] = OrderedDict()
        self.dropped_partial_frames = 0

    @property
    def partial_frame_count(self) -> int:
        return len(self._partials)

    def add_datagram(self, datagram: bytes) -> ReassembledFrame | None:
        chunk = parse_datagram(datagram)
        header = chunk.header
        partial = self._partials.get(header.frame_id)
        if partial is None:
            partial = _PartialFrame(
                frame_id=header.frame_id,
                total_chunks=header.total_chunks,
                jpeg_size=header.jpeg_size,
                sim_time_ns=header.sim_time_ns,
            )
            self._partials[header.frame_id] = partial
            self._drop_oldest_if_needed()
        else:
            self._partials.move_to_end(header.frame_id)

        partial.add(chunk)
        if not partial.complete:
            return None

        frame = partial.assemble()
        self._partials.pop(header.frame_id, None)
        return frame

    def drop_older_than(self, frame_id: int) -> int:
        """Drop partial frames older than `frame_id` and return the drop count."""

        to_drop = [key for key in self._partials if key < frame_id]
        for key in to_drop:
            self._partials.pop(key, None)
        self.dropped_partial_frames += len(to_drop)
        return len(to_drop)

    def _drop_oldest_if_needed(self) -> None:
        while len(self._partials) > self.max_partial_frames:
            self._partials.popitem(last=False)
            self.dropped_partial_frames += 1
