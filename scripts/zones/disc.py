"""The player's disc as zone_data.py reads it: a one-track MODE2/2352 cue/bin
image, and the ISO 9660 file system on it (ECMA-119), in which each zone file
is <DIR>/<DIR>.BIN."""
import hashlib
import re
from pathlib import Path

SECTOR, HEADER, USER = 2352, 24, 2048  # MODE2/2352 form 1 sectors

# ISO 9660: the primary volume descriptor, and the fields of a directory record.
PVD_SECTOR, PVD_MAGIC, PVD_ROOT = 16, b"\x01CD001", slice(156, 190)  # the root directory's record
DIR_FLAGS, DIR_NAME_LENGTH, DIR_NAME = 25, 32, 33  # byte 0 is the record's length
DIR_EXTENT, DIR_SIZE = slice(2, 6), slice(10, 14)  # the little-endian copies
IS_DIRECTORY = 2          # the flag of a directory
SELF_AND_PARENT = (b"\x00", b"\x01")  # the names of the "." and ".." records


class ZoneError(Exception):
    """An error that zone_data.py reports in one line: in this module, a disc
    image it cannot read; in zone_data.py, a zone file, a dump, a recipe or an
    argument it cannot use. main() prints it and exits with status 1, but list
    and check take a zone file's error as that file's result and go on."""


def directory_record_problem(rest):
    """Why the directory record at the start of rest cannot be read, as the
    words that follow "a directory record" in a message, or None if it can.
    The bytes in rest run to the end of the record's sector, since ISO 9660
    keeps every record within its sector. Rules that reading does not need,
    such as the padding byte after a name of even length, are not checked."""
    length = rest[0]
    if length > len(rest):
        return f"of length {length} runs past its sector"
    if length < DIR_NAME:
        return f"of length {length} is too short for its fields"
    name_length = rest[DIR_NAME_LENGTH]
    if DIR_NAME + name_length > length:
        return f"of length {length} is too short for its name of length {name_length}"
    name = rest[DIR_NAME:DIR_NAME + name_length]
    if not name.isascii():
        return f"has a name that is not ASCII: {name!r}"
    return None


class Disc:
    """A one-track MODE2/2352 cue/bin image, read through its ISO 9660 tree."""

    def __init__(self, cue):
        cue = Path(cue)
        try:
            text = cue.read_text()
        except (OSError, UnicodeDecodeError) as exc:
            raise ZoneError(f"cannot read {cue}: {exc}")
        names = re.findall(r'^\s*FILE\s+"([^"]+)"\s+BINARY\s*$', text, re.M)
        if len(names) != 1 or not re.search(r"^\s*TRACK\s+01\s+MODE2/2352\s*$",
                                            text, re.M):
            raise ZoneError(f"{cue}: expected one FILE with TRACK 01 MODE2/2352")
        self.bin = cue.parent / names[0]

    def sectors(self, lba, count):
        data = bytearray()
        try:
            with self.bin.open("rb") as f:
                for n in range(lba, lba + count):
                    f.seek(n * SECTOR + HEADER)
                    chunk = f.read(USER)
                    if len(chunk) != USER:
                        raise ZoneError(f"{self.bin}: no sector {n}")
                    data += chunk
        except OSError as exc:
            raise ZoneError(f"cannot read {self.bin}: {exc}")
        return bytes(data)

    def directory(self, lba, size):
        """(name, lba, size, is_dir) for each record but '.' and '..'. A record
        that cannot be read is a ZoneError that names its sector and byte."""
        data = self.sectors(lba, -(-size // USER))
        for start in range(0, len(data), USER):
            pos = start
            while pos < start + USER and (length := data[pos]):  # a record starts with its length
                if problem := directory_record_problem(data[pos:start + USER]):
                    where = f"sector {lba + start // USER}, byte {pos - start}"
                    raise ZoneError(f"{self.bin}: {where}: a directory record {problem}")
                rec = data[pos:pos + length]
                name = rec[DIR_NAME:DIR_NAME + rec[DIR_NAME_LENGTH]]
                if name not in SELF_AND_PARENT:
                    yield (name.decode("ascii"), little_endian(rec[DIR_EXTENT]),
                           little_endian(rec[DIR_SIZE]), bool(rec[DIR_FLAGS] & IS_DIRECTORY))
                pos += length

    def zone_files(self):
        """{"S1/S1.BIN": (lba, size), ...}: each directory's file named after it."""
        pvd = self.sectors(PVD_SECTOR, 1)
        if not pvd.startswith(PVD_MAGIC):
            raise ZoneError(f"{self.bin}: no ISO 9660 volume")
        root = pvd[PVD_ROOT]
        found = {}
        for name, lba, size, is_dir in self.directory(little_endian(root[DIR_EXTENT]),
                                                      little_endian(root[DIR_SIZE])):
            if is_dir:
                for fname, flba, fsize, fdir in self.directory(lba, size):
                    if not fdir and fname.split(";")[0] == f"{name}.BIN":
                        found[f"{name}/{name}.BIN"] = (flba, fsize)
        return found

    def read(self, lba, size):
        return self.sectors(lba, -(-size // USER))[:size]

    def image_sha256(self):
        """The sha256 of the data file, which the runtime matches against a
        package's disc_sha256 when it mounts the cue (mod_runtime.cpp sha256_file)."""
        digest = hashlib.sha256()
        try:
            with self.bin.open("rb") as f:
                while chunk := f.read(1 << 20):
                    digest.update(chunk)
        except OSError as exc:
            raise ZoneError(f"cannot read {self.bin}: {exc}")
        return digest.hexdigest()


def little_endian(field):
    return int.from_bytes(field, "little")
