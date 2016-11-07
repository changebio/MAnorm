# -*- coding: utf-8 -*-
"""
Created on Thu May 12 21:52:35 2016

@author: huangyin
"""
import numpy as np
import random
import pandas as pd
import re
import os.path
import sys

def load_peak(peaks_path,genome_path,peak_len,peak_type,center=False):
    '''
    load the peak file, and extract the from peak sequence from the genome
    '''
    
    if peak_type == "bed6col":# normal bed file
        print '%s is a 6-column bed file.'%os.path.basename(peaks_path)
        peak = pd.read_csv(peaks_path, '\t' ,names=['chr','start','end','name','summit','strand'])
        if len(peak)==0:
            print 'Warning: No peaks detected in peak file. Exiting...'
            exit(2)
        if peak['summit'].dtype != 'int64':
                print 'Invalid summit! Please use option -f to specify your peak format!'
                exit(0)
        peak['summit'] = (peak['start'] + peak['end'])//2 
        if (peak['summit']>peak['end']).any():
            print 'Invalid d.Series(minimum,index=motif_table.index)summit! Please use option -f to specify your peak format!'
            exit(0)
    else:
        print 'Invalid peak file format! Please use option -f to specify your peak format!'
        exit(1)
    if center:
        peak['seq_start'] = peak['summit'] - peak_len//2
        peak.ix[peak['seq_start']<0,'seq_start'] = 0
        peak['seq_end'] = peak['summit'] + peak_len//2
    else:
        peak['seq_start'] = peak['start']
        peak['seq_end'] = peak['end']
    n_peak = len(peak)
    genome_iter = [genome_path]*n_peak
    peak['seq'] = map(extract_sequence,genome_iter,peak['chr'],peak['seq_start'],peak['seq_end'])

    peak['seq_matrix'] = map(construct_sequence_matrix_by_strand,peak['seq'],peak['strand'])

    return peak

def extract_sequence(genome,chr,bpstart,bpend):
    # 0-based: bpstart is included while bpend is not included.
    gf = file('%s/%s'%(genome,chr))
    gf.seek(0,0)
    gf.readline()  #read the first line; the pointer is at the second line
    nbp = bpend - bpstart
    offset = bpstart + np.floor(bpstart/50) #assuming each line contains 50 characters; add 1 offset per line
    gf.seek(offset,1)
    seq_tmp = gf.read(nbp+int(np.floor(nbp/50))+1)
    seq_tmp = seq_tmp.replace('\n','')
    gf.close()
    return seq_tmp[0:nbp].upper()
    
def construct_sequence_matrix_by_strand(seq,strand):
    matrix = np.zeros((4,len(seq)))
    if strand == "+":
        for base,idx in zip(seq,np.arange(len(seq))):
            if base == 'A':
                matrix[0][idx] = 1
            elif base == 'C':
                matrix[1][idx] = 1
            elif base == 'G':
                matrix[2][idx] = 1
            elif base == 'T':
                matrix[3][idx] = 1
    else:
        for base,idx in zip(seq,np.arange(len(seq))):
            if base == 'T':
                matrix[0][idx] = 1
            elif base == 'G':
                matrix[1][idx] = 1
            elif base == 'C':
                matrix[2][idx] = 1
            elif base == 'A':
                matrix[3][idx] = 1
    return matrix    