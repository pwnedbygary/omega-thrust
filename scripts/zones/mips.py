"""The analysis of a zone file's MIPS I (R3000A) code for zone_data.py. The
game loads a zone file whole at BASE, so word index i of the file runs at
BASE + 4 * i. Besides decoding, it finds the jumps and branches (control())
and where control can go (join_points(), flow()), and reads back the value a
register holds through straight-line code (trace(), argument(), loaded())."""
import struct

BASE = 0x80120000         # every zone file loads whole at this address

# MIPS I (R3000A) encodings that the code analysis reads.
SPECIAL, REGIMM, J, JAL, BEQ, BNE, BLEZ, BGTZ = range(8)  # opcodes 0 to 7
BRANCHES = (REGIMM, BEQ, BNE, BLEZ, BGTZ)  # the conditional branches
ADDIU, ORI, LUI, LW = 0x09, 0x0D, 0x0F, 0x23
IMMEDIATE_OPS, LOADS = range(0x08, 0x10), range(0x20, 0x27)  # these write rt
# The console's coprocessors. The analysis does not model their branches (bc0f,
# bc0t, bc2f and bc2t), and no word of the disc's zone files decodes as one.
COP0, COP2 = 0x10, 0x12
COP_MOVES = (0, 2)        # rs of mfc and cfc, coprocessor ops that write rt
JR, JALR = 0x08, 0x09     # SPECIAL functions that jump through a register
ADDU, OR = 0x21, 0x25     # SPECIAL functions that move when one source is $zero
MULT_DIV = range(0x18, 0x1C)  # SPECIAL functions mult to divu, which write no rd
LINK = 0x10               # REGIMM's rt bit for bltzal and bgezal, which link
ZERO, A1, A2, A3, RA = 0, 5, 6, 7, 31  # registers


def words(blob):
    return struct.unpack_from(f"<{len(blob) // 4}I", blob)


def jal(target):
    return (JAL << 26) | (target & 0x0FFFFFFF) >> 2


def sx16(value):
    return value - 0x10000 if value & 0x8000 else value


def sx32(value):
    return value - 2**32 if value & 0x80000000 else value


def opcode(word):
    return word >> 26


def rs(word):
    return (word >> 21) & 31


def rt(word):
    return (word >> 16) & 31


def rd(word):
    return (word >> 11) & 31


def funct(word):
    return word & 0x3F


def immediate(word):
    return word & 0xFFFF


def address_of(index):
    """The address of a zone file's word index, as loaded."""
    return BASE + 4 * index


def index_of(address):
    """The word index of an address in a zone file, as loaded."""
    return (address - BASE) // 4


def jump_target(word, address):
    """Where the j or jal at address goes, within the region of the word after it."""
    return ((address + 4) & 0xF0000000) | (word & 0x03FFFFFF) << 2


def branch_target(word, index):
    """Where the branch at word index goes when taken, as a word index."""
    return index + 1 + sx16(immediate(word))


def is_call(word):
    """True for jal, jalr, bltzal and bgezal, which come back after their delay slot."""
    op = opcode(word)
    if op == SPECIAL:
        return funct(word) == JALR
    return op == JAL or (op == REGIMM and (rt(word) & LINK) != 0)


def is_move(word):
    """True for `move rd, rs`: an `addu` or an `or` with $zero as one source."""
    return opcode(word) == SPECIAL and funct(word) in (ADDU, OR) and ZERO in (rs(word), rt(word))


def control(word):
    """True for jumps and branches, whose delay slots end straight-line code.
    Branches on the console's coprocessors, COP0 and COP2, are not modelled."""
    op = opcode(word)
    return REGIMM <= op <= BGTZ or (op == SPECIAL and funct(word) in (JR, JALR))


def destination(word):
    """The register an instruction writes, if any (common MIPS I forms)."""
    op = opcode(word)
    if op == SPECIAL:
        return None if funct(word) == JR or funct(word) in MULT_DIV else rd(word)
    if op in IMMEDIATE_OPS or op in LOADS:
        return rt(word)
    if op in (COP0, COP2) and rs(word) in COP_MOVES:  # mfc0, mfc2, cfc2
        return rt(word)
    return RA if op == JAL else None


def join_points(code):
    """The word indices in the file where control can arrive other than from
    the word before, as far as the file's own code shows: the targets of its
    jumps, branches and calls, and the word each call returns to, past its
    delay slot. Entries that only pointers or the EXE lead to, such as the
    wave callbacks and the targets of jr and jalr, are not among them. Words
    of data that decode as jumps, branches or calls add join points too,
    which can only make argument() give up sooner. Branches on the console's
    coprocessors, COP0 and COP2, are not modelled, so their targets are not
    among them either."""
    joins = set()
    for i, word in enumerate(code):
        op = opcode(word)
        if op in (J, JAL):
            joins.add(index_of(jump_target(word, address_of(i))))
        elif op in BRANCHES:
            joins.add(branch_target(word, i))
        if is_call(word):
            joins.add(i + 2)
    return {join for join in joins if 0 <= join < len(code)}


def trace(seq, index, reg, first=0, steps=32):
    """Value of reg after seq[index], from straight-line lui/addiu/ori/move
    code in seq[first:index + 1]."""
    while reg != ZERO and index >= first and steps > 0:
        word = seq[index]
        op = opcode(word)
        if op == LUI and rt(word) == reg:
            return immediate(word) << 16
        if op in (ADDIU, ORI) and rt(word) == reg:
            base = trace(seq, index - 1, rs(word), first, steps - 1)
            if base is None:
                return None
            if op == ADDIU:
                return (base + sx16(immediate(word))) & 0xFFFFFFFF
            return base | immediate(word)
        if is_move(word) and rd(word) == reg:
            reg = rs(word) or rt(word)
        elif destination(word) == reg or control(word):
            return None
        index -= 1
        steps -= 1
    return 0 if reg == ZERO else None


def argument(code, joins, call, reg):
    """Register reg as the function called by the jal at code[call] receives
    it. The trace reads back no further than the last of joins
    (join_points(code)) at or before the call, since control that arrives
    there from a jump, a branch or a call's return may bring another value.
    Entries that only pointers or the EXE lead to are not known, so the trace
    can still read back past one of those."""
    # The delay slot runs before the call, so it takes the call's place in seq:
    # a path that jumps to the call runs the delay slot but not the words before.
    seq = code[:call] + code[call + 1:call + 2]
    first = max((j for j in joins if j <= call), default=0)
    return trace(seq, len(seq) - 1, reg, first)


def flow(code, entry):
    """{word index: where control goes next} for the code reached from word
    entry. A jump or branch goes to its target and, if conditional, also to
    the word after its delay slot; a call (jal, jalr, bltzal, bgezal) returns
    to the word after its slot; jr, and indices outside the file, end a path.
    Each jump, branch, call and jr leads past its delay slot: the slot runs
    on the console, but the graph has no node for it unless another path in
    the graph leads there. Branches on the console's coprocessors, COP0 and
    COP2, are not modelled."""
    graph, todo = {}, [entry]
    while todo:
        i = todo.pop()
        while 0 <= i < len(code) and i not in graph:
            word = code[i]
            op = opcode(word)
            if op == SPECIAL and funct(word) == JR:
                graph[i] = []
            elif op == J:
                graph[i] = [index_of(jump_target(word, address_of(i)))]
            elif is_call(word):
                graph[i] = [i + 2]
            elif op in BRANCHES:
                graph[i] = [branch_target(word, i), i + 2]
            else:
                graph[i] = [i + 1]
                i += 1
                continue
            todo += graph[i]
            break
    return graph


def loaded(code, start, index, reg):
    """The address of the word reg holds at word index, if an lw from word start
    on wrote reg last and the code from start to it gives the address."""
    for i in range(index - 1, start - 1, -1):
        if destination(code[i]) == reg:
            if opcode(code[i]) != LW:
                return None
            base = trace(code[start:i], i - 1 - start, rs(code[i]))
            return None if base is None else (base + sx16(immediate(code[i]))) & 0xFFFFFFFF
    return None
