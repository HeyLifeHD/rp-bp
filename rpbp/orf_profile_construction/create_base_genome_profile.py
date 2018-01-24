#! /usr/bin/env python3

import argparse
import logging
import os
import shlex
import shutil
import sys

import yaml

import riboutils.ribo_filenames as filenames

import bio_utils.bio as bio
import bio_utils.bam_utils as bam_utils
import bio_utils.fastx_utils as fastx_utils
import bio_utils.star_utils as star_utils
import misc.logging_utils as logging_utils
import misc.shell_utils as shell_utils
import misc.utils as utils

logger = logging.getLogger(__name__)

default_num_cpus = 1
default_mem = "2G"

default_flexbar_format_option = "qtrim-format"
default_quality_format = 'sanger'
default_max_uncalled = 1
default_pre_trim_left = 0

# STAR arguments
default_star_executable = "STAR"

default_align_intron_min = 20
default_align_intron_max = 100000
default_out_filter_mismatch_n_max = 1
default_out_filter_mismatch_n_over_l_max = 0.04
default_out_filter_type = "BySJout"
default_out_filter_intron_motifs = "RemoveNoncanonicalUnannotated"
default_out_sam_attributes = ["AS", "NH", "HI", "nM", "MD"]

flexbar_compression_str = "--zip-output GZ"

# the Rp-Bp pipeline does not use the transcript alignments, so do not create them
quant_mode_str = "" # '--quantMode TranscriptomeSAM'
star_out_str = "--outSAMtype BAM SortedByCoordinate"

default_tmp = None

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="") #filenames.run_riboseq_preprocessing_description)

    parser.add_argument('raw_data', help="The raw data file (fastq[.gz])")
    parser.add_argument('config', help="The (yaml) config file")
    parser.add_argument('name', help="The name for the dataset, used in the created files")

    parser.add_argument('-p', '--num-cpus', help="The number of processors to use",
        type=int, default=default_num_cpus)
    
    parser.add_argument('--mem', help="The amount of RAM to request", 
        default=default_mem)
       
    parser.add_argument('--flexbar-format-option', help="The name of the \"format\" "
        "option for flexbar. This changed from \"format\" to \"qtrim-format\" in "
        "version 2.7.", default=default_flexbar_format_option)

    parser.add_argument('-t', '--tmp', help="The location for temporary files. If not "
            "specified, program-specific temp locations are used.", default=default_tmp)

    parser.add_argument('--do-not-call', action='store_true')
    parser.add_argument('--overwrite', help="If this flag is present, existing files "
        "will be overwritten.", action='store_true')

    
    parser.add_argument('-k', '--keep-intermediate-files', help="If this flag is given, "
        "then all intermediate files will be kept; otherwise, they will be "
        "deleted. This feature is implemented piecemeal. If the --do-not-call flag "
        "is given, then nothing will be deleted.", action='store_true')

    star_utils.add_star_options(parser)
    logging_utils.add_logging_options(parser)
    args = parser.parse_args()
    logging_utils.update_logging(args)

    msg = "[create-base-genome-profile]: {}".format(' '.join(sys.argv))
    logger.info(msg)

    config = yaml.load(open(args.config))
    call = not args.do_not_call
    keep_delete_files = args.keep_intermediate_files or args.do_not_call

    # check that all of the necessary programs are callable
    programs =  [   'flexbar',
                    args.star_executable,
                    'samtools',
                    'bowtie2',
                    'remove-multimapping-reads'
                ]
    shell_utils.check_programs_exist(programs)

    required_keys = [   'riboseq_data',
                        'ribosomal_index',
                        'gtf',
                        'genome_base_path',
                        'genome_name'
                    ]
    utils.check_keys_exist(config, required_keys)

    note = config.get('note', None)

    # Step 0: Running flexbar to remove adapter sequences

    raw_data = args.raw_data
    flexbar_target = filenames.get_without_adapters_base(config['riboseq_data'], args.name, note=note)
    without_adapters = filenames.get_without_adapters_fastq(config['riboseq_data'], args.name, note=note)

    adapter_seq_str = utils.get_config_argument(config, 'adapter_sequence', 'adapter-seq')
    adapter_file_str = utils.get_config_argument(config, 'adapter_file', 'adapters')

    quality_format_str = utils.get_config_argument(config, 'quality_format', args.flexbar_format_option, 
        default=default_quality_format)
    max_uncalled_str = utils.get_config_argument(config, 'max_uncalled', default=default_max_uncalled)
    pre_trim_left_str = utils.get_config_argument(config, 'pre_trim_left', default=default_pre_trim_left)

    cmd = "flexbar {} {} {} {} -n {} {} -r {} -t {} {}".format(quality_format_str, 
        max_uncalled_str, adapter_seq_str, adapter_file_str, args.num_cpus, flexbar_compression_str, 
        raw_data, flexbar_target, pre_trim_left_str)
    in_files = [raw_data]
    out_files = [without_adapters]
    file_checkers = {
        without_adapters: fastx_utils.check_fastq_file
    }
    shell_utils.call_if_not_exists(cmd, out_files, in_files=in_files, 
        file_checkers=file_checkers, overwrite=args.overwrite, call=call)

    # Step 1: Running bowtie2 to remove rRNA alignments
    out = utils.abspath("dev","null") # we do not care about the alignments
    without_rrna = filenames.get_without_rrna_fastq(config['riboseq_data'], args.name, note=note)
    with_rrna = filenames.get_with_rrna_fastq(config['riboseq_data'], args.name, note=note)

    cmd = "bowtie2 -p {} --very-fast -x {} -U {} -S {} --un-gz {} --al-gz {}".format(
        args.num_cpus, config['ribosomal_index'], without_adapters, out, 
        without_rrna, with_rrna)
    in_files = [without_adapters]
    in_files.extend(bio.get_bowtie2_index_files(config['ribosomal_index']))
    out_files = [without_rrna, with_rrna]
    to_delete = [without_adapters]
    file_checkers = {
        without_rrna: fastx_utils.check_fastq_file
    }
    shell_utils.call_if_not_exists(cmd, out_files, in_files=in_files, 
        file_checkers=file_checkers, overwrite=args.overwrite, call=call,
        keep_delete_files=keep_delete_files, to_delete=to_delete)

    # Step 2: Running STAR to align rRNA-depleted reads to genome
    star_output_prefix = filenames.get_riboseq_bam_base(config['riboseq_data'], args.name, note=note)
    #transcriptome_bam = "{}{}".format(star_output_prefix, "Aligned.toTranscriptome.out.bam")
    genome_star_bam = "{}{}".format(star_output_prefix, "Aligned.sortedByCoord.out.bam")

    star_compression_str = "--readFilesCommand {}".format(
        shlex.quote(args.star_read_files_command))

    align_intron_min_str = utils.get_config_argument(config, 'align_intron_min', 
        'alignIntronMin', default=default_align_intron_min)
    align_intron_max_str = utils.get_config_argument(config, 'align_intron_max', 
        'alignIntronMax', default=default_align_intron_max)
    out_filter_mismatch_n_max_str = utils.get_config_argument(config, 'out_filter_mismatch_n_max', 
        'outFilterMismatchNmax', default=default_out_filter_mismatch_n_max)
    out_filter_mismatch_n_over_l_max_str = utils.get_config_argument(config, 'out_filter_mismatch_n_over_l_max',
        'outFilterMismatchNoverLmax', default=default_out_filter_mismatch_n_over_l_max)
    out_filter_type_str = utils.get_config_argument(config, 'out_filter_type', 
        'outFilterType', default=default_out_filter_type)
    out_filter_intron_motifs_str = utils.get_config_argument(config, 'out_filter_intron_motifs', 
        'outFilterIntronMotifs', default=default_out_filter_intron_motifs)
    out_sam_attributes_str = utils.get_config_argument(config, 'out_sam_attributes', 
        'outSAMattributes', default=default_out_sam_attributes)

    star_tmp_str = ""
    if args.tmp is not None:
        star_tmp_name = "STAR_rpbp"
        star_tmp_dir = star_utils.create_star_tmp(args.tmp, star_tmp_name)
        star_tmp_str = "--outTmpDir {}".format(star_tmp_dir)

    mem_bytes = utils.human2bytes(args.mem)
    star_mem_str = "--limitBAMsortRAM {}".format(mem_bytes)

    sjdbGTFtag_str = ""
    # if GFF3 specs, then we need to inform STAR
    # whether we have de novo or not, the format of "config['gtf']" has precedence
    use_gff3_specs = config['gtf'].endswith('gff')
    gtf_file = filenames.get_gtf(config['genome_base_path'],
        config['genome_name'], is_gff3=use_gff3_specs, is_star_input=True)
    if use_gff3_specs:
        sjdbGTFtag_str = "--sjdbGTFtagExonParentTranscript Parent"

    cmd = ("{} --runThreadN {} {} --genomeDir {} --sjdbGTFfile {} {} --readFilesIn {} "
        "{} {} {} {} {} {} {} {} --outFileNamePrefix {} {} {} {}".format(args.star_executable,
        args.num_cpus, star_compression_str, config['star_index'], gtf_file, sjdbGTFtag_str,
        without_rrna, align_intron_min_str, align_intron_max_str, out_filter_mismatch_n_max_str,
        out_filter_type_str, out_filter_intron_motifs_str, quant_mode_str,
        out_filter_mismatch_n_over_l_max_str, out_sam_attributes_str, star_output_prefix,
        star_out_str, star_tmp_str, star_mem_str))
    in_files = [without_rrna]
    in_files.extend(star_utils.get_star_index_files(config['star_index']))
    #out_files = [transcriptome_bam, genome_star_bam]
    to_delete = [without_rrna]
    out_files = [genome_star_bam]
    file_checkers = {
        #transcriptome_bam: bam_utils.check_bam_file,
        genome_star_bam: bam_utils.check_bam_file
    }
    shell_utils.call_if_not_exists(cmd, out_files, in_files=in_files, 
        file_checkers=file_checkers, overwrite=args.overwrite, call=call,
        keep_delete_files=keep_delete_files, to_delete=to_delete)
    
    # now, we need to symlink the (genome) STAR output to that expected by the rest of the pipeline
    genome_sorted_bam = filenames.get_riboseq_bam(config['riboseq_data'], args.name, note=note)

    if os.path.exists(genome_star_bam):
        shell_utils.create_symlink(genome_star_bam, genome_sorted_bam, call)
    else:
        msg = ("Could not find the STAR genome bam alignment file. Unless "
        "--do-not-call was given, this is a problem.")
        logger.warning(msg)

    # create the bamtools index
    cmd = "samtools index -b {}".format(genome_sorted_bam)
    shell_utils.check_call(cmd, call=call)

    # check if we want to keep multimappers
    if 'keep_riboseq_multimappers' in config:
        return

    # remove multimapping reads from the genome file
    tmp_str = ""
    if args.tmp is not None:
        tmp_str = "--tmp {}".format(args.tmp)

    unique_genome_filename = filenames.get_riboseq_bam(config['riboseq_data'], 
        args.name, is_unique=True, note=note)

    cmd = "remove-multimapping-reads {} {} {}".format(genome_sorted_bam, 
        unique_genome_filename, tmp_str)

    in_files = [genome_sorted_bam]
    out_files = [unique_genome_filename]
    to_delete = [genome_star_bam, genome_sorted_bam]
    file_checkers = {
        unique_genome_filename: bam_utils.check_bam_file
    }
    shell_utils.call_if_not_exists(cmd, out_files, in_files=in_files, 
        file_checkers=file_checkers, overwrite=args.overwrite, call=call,
        keep_delete_files=keep_delete_files, to_delete=to_delete)
   
if __name__ == '__main__':
    main()
