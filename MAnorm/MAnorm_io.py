# coding=utf-8
# MAnorm的输入输出都在这个脚本里面处理
from numpy.ma import log2, log10
import matplotlib

from peaks import Peak, get_peaks_mavalues, get_peaks_normed_mavalues, get_peaks_pvalues, \
    _add_peaks, _sort_peaks_list


matplotlib.use('Agg')
from matplotlib import pyplot as plt
import numpy as np
import pysam

def _get_reads_position(reads_fp, shift):
    """
    从read文件中获取所有read的点位置信息，我们将read的位置当成点来处理。
    read文件要求前三列是chr, start, end,第六列是strand(bed格式), 列之间以\t分隔
    :param shift: <int>平移量
    :param reads_fp: read文件路径
    :return: 所有read记录的位点
    """
    position = {}
    with open(reads_fp) as fi:
        for li in fi:
            sli = li.split('\t')
            chrm, start, end, strand = sli[0].strip(), int(sli[1]), int(sli[2]), sli[5].strip()
            pos = start + shift if strand is '+' else end - shift
            try:
                position[chrm].append(pos)
            except KeyError:
                position[chrm] = []
                position[chrm].append(pos)
    # 返回排序后的reads的位点信息
    return {key: sorted(position[key]) for key in position.keys()}

def _get_bam_position(reads_fp,shift):
    """
    read bam file
    :param reads_fp: <str>read file path
    :param shift: <int>The arbitrary shift size in bp
    :return: all read position after shift
    """
    position = {}    
    with pysam.AlignmentFile(reads_fp,"rb") as samfile:
        for read in samfile.fetch():
            chrm,start,end,strand = samfile.getrname(read.tid),read.pos,read.aend,"-" if read.is_reverse==True else "+"
            pos = start + shift if strand is "+" else end - shift
            try:
                position[chrm].append(pos)
            except KeyError:
                position[chrm]=[]
                position[chrm].append(pos)
        return {key: sorted(position[key]) for key in position.keys()}
            

def _get_read_length(reads_fp):
    """
    一般read文件中的read长度都是一样的，通过读取第一行的read信息获取此read文件中read的长度。
    :param reads_fp: read文件
    :return: read长度
    """
    with open(reads_fp) as fi:
        for li in fi:
            sli = li.split('\t')
            return int(sli[2]) - int(sli[1])


def read_reads(reads_fp, shift):
    if ".bed" in reads_fp :
        return _get_reads_position(reads_fp, shift)
    elif ".bam" in reads_fp :
        return _get_bam_position(reads_fp,shift)
    else :
        print "please get right read input"
    


def _read_peaks(peak_fp):
    """
    peak文件要求前三列分别是chrm, start, end. 可以有第四列summit,
    summit要求是相对于start的位置（和macs的结果一样）
    以#开头的行会跳过，列之间用制表符分隔开
    :param peak_fp: peak文件路径
    :return: Peak的字典
    """
    pks = {}
    with open(peak_fp) as fi:
        for li in fi:
            if li.startswith('#'):
                continue
            sli = li.split('\t')
            chrm = sli[0].strip()
            try:
                # pk = Peak(chrm, int(sli[1]), int(sli[2]))
                pk = Peak(chrm, int(sli[1]), int(sli[2]), int(sli[3].strip()))
            except:
                pk = Peak(chrm, int(sli[1]), int(sli[2]))
            try:
                pks[chrm].append(pk)
            except KeyError:
                pks[chrm] = []
                pks[chrm].append(pk)
    return pks


def _read_macs_xls_peaks(peak_fp):
    """
    macs xls peak的格式如下：
    # This file is generated by MACS
    # ARGUMENTS LIST:
    # name = H1hesc_H3K27ac
    # format = BED
    # ChIP-seq file = ERR361900_H1hesc_H3K27ac.bed
    # control file = ERR361907_H1hESCs_input.bed
    # effective genome size = 2.70e+09
    # tag size = 33
    # band width = 300
    # model fold = 32
    # pvalue cutoff = 1.00e-05
    # Ranges for calculating regional lambda are : peak_region,1000,5000,10000
    # unique tags in treatment: 20362172
    # total tags in treatment: 23716419
    # unique tags in control: 17987977
    # total tags in control: 19711008
    # d = 164
    chr     start   end     length  summit  tags    -10*log10(pvalue)       fold_enrichment FDR(%)
    chr1    713915  714866  952     555     115     472.37  18.43   5.33
    chr1    761943  763542  1600    1306    204     373.20  10.53   8.45
    chr1    839510  840672  1163    449     77      69.35   5.60    100
    :param peak_fp: macs xls peaks file path
    :return: peaks字典
    """
    pks = {}
    with open(peak_fp) as fi:
        for li in fi:
            if li.startswith('#'):
                continue
            sli = li.split('\t')
            chrm = sli[0].strip()
            try:
                # pk = Peak(chrm, int(sli[1]), int(sli[2]))
                pk = Peak(chrm, int(sli[1]), int(sli[2]), int(sli[4]))
            except:
                continue
            try:
                pks[chrm].append(pk)
            except KeyError:
                pks[chrm] = []
                pks[chrm].append(pk)
    return pks


def read_peaks(peak_fp):
    if peak_fp.endswith('.xls'):
        return _read_macs_xls_peaks(peak_fp)
    else:
        return _read_peaks(peak_fp)


def output_normalized_peaks(pks_unique, pks_common, file_name, rds1_name, rds2_name):
    """
    输出MAnorm标准化后的结果
    """
    fo = open(file_name, 'w')
    # declaration = manorm_file_declaration
    header = \
        '\t'.join(['chr', 'start', 'end', 'summit', 'M_value', 'A_value', 'P_value', 'Peak_Group',
                   'normalized_read_density_in_%s' % rds1_name,
                   'normalized_read_density_in_%s\n' % rds2_name])
    # fo.write(declaration)
    fo.write(header)
    for chrm in pks_unique.keys():
        for pk in pks_unique[chrm]:
            cnt = (pk.chrm, pk.start, pk.end, pk.summit - pk.start,
                   pk.normed_mvalue, pk.normed_avalue, str(pk.pvalue), 'unique',
                   pk.normed_read_density1, pk.read_density2,)
            fo.write('\t'.join(
                ['%s', '%d', '%d', '%d', '%f', '%f', '%s', '%s', '%f', '%f']) % cnt + '\n')
    for chrm in pks_common.keys():
        for pk in pks_common[chrm]:
            cnt = (pk.chrm, pk.start, pk.end, pk.summit - pk.start,
                   pk.normed_mvalue, pk.normed_avalue, str(pk.pvalue), 'common',
                   pk.normed_read_density1, pk.read_density2)
            fo.write('\t'.join(
                ['%s', '%d', '%d', '%d', '%f', '%f', '%s', '%s', '%f', '%f']) % cnt + '\n')
    fo.close()


def output_3set_normalized_peaks(pks1_unique, merged_pks, pks2_unique, file_name, pks1_name,
                                 pks2_name, rds1_name, rds2_name):
    """
    输出pks1_unique, pks2_unique, merged_pks所有的peaks
    """
    fo = open(file_name, 'w')
    # declaration = manorm_file_declaration
    header = '\t'.join(
        ['chr', 'start', 'end', 'summit', 'M_value', 'A_value', 'P_value', 'Peak_Group',
         'normalized_read_density_in_%s' % rds1_name,
         'normalized_read_density_in_%s\n' % rds2_name])
    # fo.write(declaration)
    fo.write(header)
    for chrm in pks1_unique.keys():
        for pk in pks1_unique[chrm]:
            cnt = (pk.chrm, pk.start, pk.end, pk.summit - pk.start,
                   pk.normed_mvalue, pk.normed_avalue, str(pk.pvalue), '%s_unique' % pks1_name,
                   pk.normed_read_density1, pk.read_density2)
            fo.write('\t'.join(
                ['%s', '%d', '%d', '%d', '%f', '%f', '%s', '%s', '%f', '%f']) % cnt + '\n')
    for chrm in merged_pks.keys():
        for pk in merged_pks[chrm]:
            cnt = (pk.chrm, pk.start, pk.end, pk.summit - pk.start,
                   pk.normed_mvalue, pk.normed_avalue, str(pk.pvalue), 'merged_common_peak',
                   pk.normed_read_density1, pk.read_density2)
            fo.write('\t'.join(
                ['%s', '%d', '%d', '%d', '%f', '%f', '%s', '%s', '%f', '%f']) % cnt + '\n')
    for chrm in pks2_unique.keys():
        for pk in pks2_unique[chrm]:
            cnt = (pk.chrm, pk.start, pk.end, pk.summit - pk.start,
                   pk.normed_mvalue, pk.normed_avalue, str(pk.pvalue), '%s_unique' % pks2_name,
                   pk.normed_read_density1, pk.read_density2)
            fo.write('\t'.join(
                ['%s', '%d', '%d', '%d', '%f', '%f', '%s', '%s', '%f', '%f']) % cnt + '\n')
    fo.close()


def draw_figs_to_show_data(pks1_uni, pks2_uni, merged_pks, pks1_name, pks2_name, ma_fit,
                           reads1_name, reads2_name):
    """
    draw four figures to show data before and after rescaled
    """
    pks_3set = [pks1_uni, pks2_uni, merged_pks]
    pks1_name = ' '.join([pks1_name, 'unique'])
    pks2_name = ' '.join([pks2_name, 'unique'])
    merged_pks_name = 'merged common peaks'
    pks_names = [pks1_name, pks2_name, merged_pks_name]
    colors = 'bgr'
    a_max = 0
    a_min = 10000
    plt.figure(1).set_size_inches(16, 12)
    for (idx, pks) in enumerate(pks_3set):
        mvalues, avalues = get_peaks_mavalues(pks)
        if len(avalues) != 0:
            a_max = max(max(avalues), a_max)
            a_min = min(min(avalues), a_min)
        plt.scatter(avalues, mvalues, s=10, c=colors[idx])
    plt.xlabel('A value')
    plt.ylabel('M value')
    plt.grid(axis='y')
    plt.legend(pks_names, loc='best')
    plt.title('before rescale')

    # plot the fitting model into figure 1
    x = np.arange(a_min, a_max, 0.01)
    y = ma_fit[1] * x + ma_fit[0]
    plt.plot(x, y, '-', color='k')
    plt.savefig('before_rescale.png')

    # plot the scatter plots of read count in merged common peaks between two chip-seq sets
    plt.figure(2).set_size_inches(16, 12)
    rd_min = 1000
    rd_max = 0
    rds_density1, rds_density2 = [], []
    for key in merged_pks.keys():
        for pk in merged_pks[key]:
            rds_density1.append(pk.read_density1), rds_density2.append(pk.read_density2)
    rd_max = max(max(log2(rds_density1)), rd_max)
    rd_min = min(min(log2(rds_density1)), rd_min)
    plt.scatter(log2(rds_density1), log2(rds_density2), s=10, c='r', label=merged_pks_name,
                alpha=0.5)
    plt.xlabel(' log2 read density' + ' by ' + '"' + reads1_name + '" reads')
    plt.ylabel(' log2 read density' + ' by ' + '"' + reads2_name + '" reads')
    plt.grid(axis='y')
    plt.legend(loc='upper left')
    plt.title('Fitting Model via common peaks')
    rx = np.arange(rd_min, rd_max, 0.01)
    ry = (2 - ma_fit[1]) * rx / (2 + ma_fit[1]) - 2 * ma_fit[0] / (2 + ma_fit[1])
    plt.plot(rx, ry, '-', color='k')
    plt.savefig('log2_read_density.png')

    # plot the MA plot after rescale
    plt.figure(3).set_size_inches(16, 12)
    for (idx, pks) in enumerate(pks_3set):
        normed_mvalues, normed_avalues = get_peaks_normed_mavalues(pks)
        plt.scatter(normed_avalues, normed_mvalues, s=10, c=colors[idx])
    plt.xlabel('A value')
    plt.ylabel('M value')
    plt.grid(axis='y')
    plt.legend(pks_names, loc='best')
    plt.title('after rescale')
    plt.savefig('after_rescale.png')

    # generate MA plot for this set of peaks together with p-value
    plt.figure(4).set_size_inches(16, 12)
    for (idx, pks) in enumerate(pks_3set):
        normed_mvalues, normed_avalues = get_peaks_normed_mavalues(pks)
        colors = -log10(get_peaks_pvalues(pks))
        for i, c in enumerate(colors):
            if c > 50:
                colors[i] = 50
        plt.scatter(normed_avalues, normed_mvalues, s=10, c=colors, cmap='jet')
    plt.colorbar()
    plt.grid(axis='y')
    plt.xlabel('A value')
    plt.ylabel('M value')
    plt.title('-log10(P-value)')
    plt.savefig('-log10_P-value.png')
    plt.close()


def output_peaks_mvalue_2wig_file(pks1_uni, pks2_uni, merged_pks, comparison_name):
    """
    output of peaks with normed m value and p values
    """
    print 'output wig files ... '

    peaks = _add_peaks(_add_peaks(pks1_uni, merged_pks), pks2_uni)
    f_2write = open('_'.join([comparison_name, 'peaks_Mvalues.wig']), 'w')
    f_2write.write('browser position chr11:5220000-5330000\n')
    f_2write.write('track type=wiggle_0 name=%s' % comparison_name +
                   ' visibility=full autoScale=on color=255,0,0 ' +
                   ' yLineMark=0 yLineOnOff=on priority=10\n')
    for chr_id in peaks.keys():
        f_2write.write('variableStep chrom=' + chr_id + ' span=100\n')
        pks_chr = peaks[chr_id]
        sorted_pks_chr = _sort_peaks_list(pks_chr, 'summit')
        # write sorted peak summit and m-value to file
        [f_2write.write('\t'.join(['%d' % pk.summit, '%s\n' % str(pk.normed_mvalue)])) for pk in
         sorted_pks_chr]
    f_2write.close()

    f_2write = open('_'.join([comparison_name, 'peaks_Pvalues.wig']), 'w')
    f_2write.write('browser position chr11:5220000-5330000\n')
    f_2write.write('track type=wiggle_0 name=%s(-log10(p-value))' % comparison_name +
                   ' visibility=full autoScale=on color=255,0,0 ' +
                   ' yLineMark=0 yLineOnOff=on priority=10\n')
    for chr_id in peaks.keys():
        f_2write.write('variableStep chrom=' + chr_id + ' span=100\n')
        pks_chr = peaks[chr_id]
        sorted_pks_chr = _sort_peaks_list(pks_chr, 'summit')
        # write sorted peak summit and m-value to file
        [f_2write.write('\t'.join(['%d' % pk.summit, '%s\n' % str(-log10(pk.pvalue))])) for pk in
         sorted_pks_chr]
    f_2write.close()


def output_unbiased_peaks(pks1_uni, pks2_uni, merged_pks, unbiased_mvalue, overlap_dependent):
    """
    输出没有显著差异的peak
    """
    print 'define unbiased peaks: '

    if not overlap_dependent:
        pks = _add_peaks(_add_peaks(pks1_uni, merged_pks), pks2_uni)
        name = 'all_peaks'
    else:
        pks = merged_pks
        name = 'merged_common_peaks'

    file_bed = open('unbiased_peaks_of_%s' % name + '.bed', 'w')
    # file_bed.write(bed_peak_header)
    i = 0
    for key in pks.keys():
        for pk in pks[key]:
            if abs(pk.normed_mvalue) < unbiased_mvalue:
                i += 1
                line = '\t'.join([pk.chrm, '%d' % pk.start, '%d' % pk.end, 'from_%s_%d' % (name, i),
                                  '%s\n' % str(pk.normed_mvalue)])
                file_bed.write(line)
    print 'filter %d unbiased peaks' % i
    file_bed.close()


def output_biased_peaks(pks1_uni, pks2_uni, merged_pks, biased_mvalue, biased_pvalue,
                        overlap_dependent):
    """
    输出有显著差异的peaks
    """
    print 'define biased peaks:'

    if not overlap_dependent:
        pks = _add_peaks(_add_peaks(pks1_uni, merged_pks), pks2_uni)
        name = 'all_peaks'
    else:
        pks = _add_peaks(pks1_uni, pks2_uni)
        name = 'unique_peaks'

    file_bed_over = open('M_over_%.2f_biased_peaks_of_%s' % (biased_mvalue, name) + '.bed', 'w')
    # file_bed_over.write(bed_peak_header)
    file_bed_less = open('M_less_-%.2f_biased_peaks_of_%s' % (biased_mvalue, name) + '.bed', 'w')
    # file_bed_less.write(bed_peak_header)
    i, j = 0, 0
    for key in pks.keys():
        for pk in pks[key]:
            if pk.pvalue < biased_pvalue:
                if pk.normed_mvalue > biased_mvalue:
                    i += 1
                    line = '\t'.join(
                        [pk.chrm, '%d' % pk.start, '%d' % pk.end, 'from_%s_%d' % (name, i),
                         '%s\n' % str(pk.normed_mvalue)])
                    file_bed_over.write(line)
                if pk.normed_mvalue < -biased_mvalue:
                    j += 1
                    line = '\t'.join(
                        [pk.chrm, '%d' % pk.start, '%d' % pk.end, 'from_%s_%d' % (name, j),
                         '%s\n' % str(pk.normed_mvalue)])
                    file_bed_less.write(line)
    print 'filter %d biased peaks' % (i + j)
    file_bed_over.close(), file_bed_less.close()


def test_read_reads():
    pos, leng = read_reads('1-reads.bed', 100)
    print leng


def test_read_peaks():
    pks = _read_peaks('1_peaks')
    print pks.keys()
    print 'Done.'


if __name__ == '__main__':
    import time

    start_time = time.clock()

    # test_get_reads_position()
    # test_read_peaks()
    test_read_reads()

    consumption_time = time.clock() - start_time
    print consumption_time