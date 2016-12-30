"""BAM utilities."""
from __future__ import absolute_import, division, print_function

import logging
import os
from itertools import islice

import pysam


def bam_total_reads(bam_fname):
    """Count the total number of mapped reads in a BAM file.

    Uses the BAM index to do this quickly.
    """
    lines = pysam.idxstats(bam_fname)
    if isinstance(lines, basestring):
        lines = lines.splitlines()
    tot_mapped_reads = 0
    for line in lines:
        _seqname, _seqlen, nmapped, _nunmapped = line.split()
        tot_mapped_reads += int(nmapped)
    return tot_mapped_reads


def ensure_bam_index(bam_fname):
    """Ensure a BAM file is indexed, to enable fast traversal & lookup.

    For MySample.bam, samtools will look for an index in these files, in order:

    - MySample.bam.bai
    - MySample.bai
    """
    if os.path.isfile(bam_fname + '.bai'):
        # MySample.bam.bai
        bai_fname = bam_fname + '.bai'
    else:
        # MySample.bai
        bai_fname = bam_fname[:-1] + 'i'
    if not is_newer_than(bai_fname, bam_fname):
        logging.info("Indexing BAM file %s", bam_fname)
        pysam.index(bam_fname)
        bai_fname = bam_fname + '.bai'
    assert os.path.isfile(bai_fname), \
            "Failed to generate index " + bai_fname
    return bai_fname


def ensure_bam_sorted(bam_fname, by_name=False, span=50):
    """Test if the reads in a BAM file are sorted as expected.

    by_name=True: reads are expected to be sorted by query name. Consecutive
    read IDs are in alphabetical order, and read pairs appear together.

    by_name=False: reads are sorted by position. Consecutive reads have
    increasing position.
    """
    if by_name:
        # Compare read IDs
        def out_of_order(read, prev):
            return not (prev is None or
                        prev.qname <= read.qname)
    else:
        # Compare read locations
        def out_of_order(read, prev):
            return not (prev is None or
                        read.tid != prev.tid or
                        prev.pos <= read.pos)

    # ENH - repeat at 50%, ~99% through the BAM
    bam = pysam.Samfile(bam_fname, 'rb')
    last_read = None
    for read in islice(bam, span):
        if out_of_order(read, last_read):
            return False
        last_read = read
    return True


def is_newer_than(target_fname, orig_fname):
    if not os.path.isfile(target_fname):
        return False
    return (os.stat(target_fname).st_mtime >= os.stat(orig_fname).st_mtime)