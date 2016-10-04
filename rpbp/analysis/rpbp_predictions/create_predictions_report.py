#! /usr/bin/env python3

import argparse
import logging
import os
import sys
import yaml

import misc.latex as latex
import misc.logging_utils as logging_utils
import misc.slurm as slurm
import misc.utils as utils

import riboutils.ribo_filenames as filenames
import riboutils.ribo_utils as ribo_utils

logger = logging.getLogger(__name__)

default_project_name = "riboseq"
default_note = None
default_num_cpus = 1
default_image_type = 'eps'

default_uniprot = ""
default_uniprot_label = "UniRef"


def create_figures(name, is_replicate, config, args):
    """ This function creates all of the figures in the prediction report
        for the given dataset.
    """

    # by default, we will not include chisq
    chisq_values = [False]
    if args.show_chisq:
        chisq_values = [True, False]

    logging_str = logging_utils.get_logging_options_string(args)

    note_str = config.get('note', None)
    out_note_str = config.get('note', None)
    if args.note is not None and len(args.note) > 0:
        out_note_str = args.note

    image_type_str = "--image-type {}".format(args.image_type)
    num_cpus_str = "--num-cpus {}".format(args.num_cpus)
   
    fraction = config.get('smoothing_fraction', None)
    reweighting_iterations = config.get('smoothing_reweighting_iterations', None)

    # if this is a replicate, we do not worry about lengths and offsets
    if is_replicate:
        lengths = None
        offsets = None
    else:
        try:
            lengths, offsets = ribo_utils.get_periodic_lengths_and_offsets(config, name)
        except FileNotFoundError:
            msg = "Could not parse out lengths and offsets for sample: {}. Skipping".format(name)
            logger.error(msg)
            return
        
    unsmoothed_profiles = filenames.get_riboseq_profiles(config['riboseq_data'], name, 
            length=lengths, offset=offsets, is_unique=True, note=note_str, is_smooth=False)



    msg = "{}: creating the ORF types pie charts".format(name)
    logger.info(msg)

    for is_grouped in [True, False]:
        for is_chisq in chisq_values:
            for is_filtered in [True, False]:

                is_grouped_str = ""
                if is_grouped:
                    is_grouped_str = ", Grouped"

                is_filtered_str = ""
                if is_filtered:
                    is_filtered_str = ", Filtered"
                
                if is_chisq:
                    title_str = "--title \"{}{}{}, Rp-$\chi^2$\"".format(name, is_grouped_str, is_filtered_str)
                    f = None
                    rw = None

                    orfs = filenames.get_riboseq_predicted_orfs(config['riboseq_data'], 
                        name, length=lengths, offset=offsets, is_unique=True, note=note_str, 
                        is_chisq=True, is_filtered=is_filtered)

                else:
                    title_str = "--title \"{}{}{}, Rp-Bp\"".format(name, is_grouped_str, is_filtered_str)
                    f = fraction
                    rw = reweighting_iterations
                    orfs = filenames.get_riboseq_predicted_orfs(config['riboseq_data'], 
                        name, length=lengths, offset=offsets, is_unique=True, note=note_str, 
                        fraction=f, reweighting_iterations=rw, 
                        is_filtered=is_filtered)


                use_groups_str = ""
                if is_grouped:
                    use_groups_str = "--use-groups"
                
                orf_types_pie_chart = filenames.get_orf_types_pie_chart(
                    config['riboseq_data'], name, length=lengths, offset=offsets, 
                    is_unique=True, note=out_note_str, image_type=args.image_type,
                    fraction=f, reweighting_iterations=rw,
                    is_grouped=is_grouped, is_chisq=is_chisq, is_filtered=is_filtered)

                cmd = "create-orf-types-pie-chart {} {} {} {}".format(orfs, orf_types_pie_chart,
                    title_str, use_groups_str)
                in_files = [orfs]
                out_files = [orf_types_pie_chart]
                utils.call_if_not_exists(cmd, out_files, in_files=in_files, overwrite=args.overwrite)

    
    msg = "{}: creating the ORF length distributions line graph".format(name)
    logger.info(msg)

    uniprot_str = ""
    uniprot_label_str = ""
    if os.path.exists(args.uniprot):
        uniprot_str = "--uniprot {}".format(args.uniprot)
        uniprot_label_str = "--uniprot-label \"{}\"".format(args.uniprot_label)

    for is_grouped in [True, False]:
        for is_chisq in chisq_values:
            
            if is_chisq:
                title_str = "--title \"{}, Rp-$\chi^2$\"".format(name)
                f = None
                rw = None
                
                orfs = filenames.get_riboseq_predicted_orfs(config['riboseq_data'], 
                    name, length=lengths, offset=offsets, is_unique=True, note=note_str, 
                    is_chisq=True)

            else:
                title_str = "--title \"{}, Rp-Bp\"".format(name)
                f = fraction
                rw = reweighting_iterations

                orfs = filenames.get_riboseq_predicted_orfs(config['riboseq_data'], 
                    name, length=lengths, offset=offsets, is_unique=True, note=note_str, 
                    fraction=f, reweighting_iterations=rw) 


            use_groups_str = ""
            if is_grouped:
                use_groups_str = "--use-groups"
            
            orf_length_line_graph = filenames.get_orf_length_distribution_line_graph(
                config['riboseq_data'], name, length=lengths, offset=offsets, 
                is_unique=True, note=out_note_str, image_type=args.image_type,
                fraction=f, reweighting_iterations=rw,
                is_grouped=is_grouped, is_chisq=is_chisq)

            cmd = ("create-orf-length-distribution-line-graph {} {} {} {} {} {}".format(
                orfs, orf_length_line_graph, title_str, use_groups_str, 
                uniprot_str, uniprot_label_str))

            in_files = [orfs]
            out_files = [orf_length_line_graph]
            utils.call_if_not_exists(cmd, out_files, in_files=in_files, overwrite=args.overwrite)

    msg = "{}: creating the ORF type metagene profiles".format(name)
    logger.info(msg)

    for is_chisq in chisq_values:
        
        if is_chisq:
            title_str = "--title \"{}, Rp-$\chi^2$\"".format(name)
            f = None
            rw = None
            is_smooth = False
            profiles = unsmoothed_profiles
    
            orfs = filenames.get_riboseq_predicted_orfs(config['riboseq_data'], 
                name, length=lengths, offset=offsets, is_unique=True, note=note_str, 
                is_chisq=True, is_filtered=is_filtered)

        else:
            title_str = "--title \"{}, Rp-Bp\"".format(name)
            f = fraction
            rw = reweighting_iterations
            is_smooth = False
            profiles = unsmoothed_profiles

            orfs = filenames.get_riboseq_predicted_orfs(config['riboseq_data'], 
                name, length=lengths, offset=offsets, is_unique=True, note=note_str, 
                fraction=f, reweighting_iterations=rw) 

        
        orf_type_profile_base = filenames.get_orf_type_profile_base(
            config['riboseq_data'], name, length=lengths, offset=offsets, 
            is_unique=True, note=out_note_str, 
            fraction=f, reweighting_iterations=rw,
            is_chisq=is_chisq)

        strand = "+"
        orf_type_profiles_forward = [
            filenames.get_orf_type_profile_image(orf_type_profile_base, orf_type, strand, args.image_type)
                for orf_type in ribo_utils.orf_types
        ]
        
        strand = "-"
        orf_type_profiles_reverse = [
            filenames.get_orf_type_profile_image(orf_type_profile_base, orf_type, strand, args.image_type)
                for orf_type in ribo_utils.orf_types
        ]

        cmd = ("visualize-orf-type-metagene-profiles {} {} {} {} {} {}".format(
            orfs, profiles, orf_type_profile_base, title_str, 
            image_type_str, logging_str))

        in_files = [orfs]
        out_files = orf_type_profiles_forward + orf_type_profiles_reverse
        utils.call_if_not_exists(cmd, out_files, in_files=in_files, overwrite=args.overwrite)

    msg = "{}: creating the RPKM-BF scatter plots".format(name)
    logger.info(msg)

    bf_rpkm_scatter_plot = filenames.get_bf_rpkm_scatter_plot(config['riboseq_data'], name, 
        length=lengths, offset=offsets, 
        is_unique=True, note=out_note_str, image_type=args.image_type,
        fraction=f, reweighting_iterations=rw)

    title_str = "--title \"{}, RPKM vs. Bayes factor\"".format(name)

    is_replicate_str = ""
    if is_replicate:
        is_replicate_str = "--is-replicate"

    cmd = "create-bf-rpkm-scatter-plot {} {} {} {} {}".format(args.config, name, 
        bf_rpkm_scatter_plot, is_replicate_str, title_str)

    in_files = [args.config]
    out_files = [bf_rpkm_scatter_plot]
    utils.call_if_not_exists(cmd, out_files, in_files=in_files, overwrite=args.overwrite)





def create_all_figures(config, args):
    
    # first, handle all of the regular datasets
    sample_names = sorted(config['riboseq_samples'].keys())

    is_replicate = False
    for sample_name in sample_names:
        create_figures(sample_name, is_replicate, config, args)

    # now, if the config file specifies replicates, create reports for those
    if 'riboseq_biological_replicates' not in config:
        return

    replicate_names = sorted(ribo_utils.get_riboseq_replicates(config).keys())
    is_replicate = True
    for replicate_name in replicate_names:
        create_figures(replicate_name, is_replicate, config, args)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="This script creates the plots which detail the basic characteristics "
        "of the ORF predictions from the Rp-Bp pipeline. It also creates and compiles (if "
        "possible) a latex report for them.")

    parser.add_argument('config', help="The (yaml) config file")
    parser.add_argument('out', help="The base output directory for the latex report")

    parser.add_argument('--uniprot', help="The uniprot ORF lengths, if available", 
        default=default_uniprot)
    parser.add_argument('--uniprot-label', help="The label to use for the uniprot ORFs in "
        "the plot", default=default_uniprot_label)
    
    parser.add_argument('--image-type', help="The format of the image files. This must be "
        "a format usable by matplotlib.", default=default_image_type)

    parser.add_argument('--overwrite', help="If this flag is present, existing files will "
        "be overwritten.", action='store_true')
        
    parser.add_argument('--note', help="If this option is given, it will be used in the "
        "filenames.\n\nN.B. This REPLACES the note in the config file.", default=default_note)

    parser.add_argument('--show-chisq', help="If this flag is given, then the "
        "results from Rp-chi will be included in the document; otherwise, they "
        "will not be created or shown.", action='store_true')

    slurm.add_sbatch_options(parser)
    logging_utils.add_logging_options(parser)
    args = parser.parse_args()
    logging_utils.update_logging(args)

    config = yaml.load(open(args.config))
    
    programs =  [   
        'create-orf-length-distribution-line-graph',
        'create-orf-types-pie-chart',
        'visualize-orf-type-metagene-profiles'
    ]
    utils.check_programs_exist(programs)
    
    required_keys = [
        'riboseq_data',
        'riboseq_samples'
    ]
    utils.check_keys_exist(config, required_keys)

    if args.use_slurm:
        cmd = ' '.join(sys.argv)
        slurm.check_sbatch(cmd, args=args)
        return

    # by default, we will not include chisq
    chisq_values = [False]
    if args.show_chisq:
        chisq_values = [True, False]
    
    # make sure the path to the output file exists
    os.makedirs(args.out, exist_ok=True)

    # first, create all of the figures
    create_all_figures(config, args)

    note_str = config.get('note', None)
    out_note_str = note_str

    if args.note is not None and len(args.note) > 0:
        out_note_str = args.note
    
    fraction = config.get('smoothing_fraction', None)
    reweighting_iterations = config.get('smoothing_reweighting_iterations', None)

    project_name = config.get("project_name", default_project_name)
    title = "Rp-Bp prediction analysis for {}".format(project_name)
    abstract = "This document shows the results of the Rp-Bp pipeline analysis."

    header = latex.get_header_text(title, abstract)
    footer = latex.get_footer_text()

    tex_file = os.path.join(args.out, "prediction-report.tex")

    
    with open(tex_file, 'w') as out:

        out.write(header)
        out.write("\n")

        ### ORF type distributions
        title = "Predicted ORF type distributions"
        latex.section(out, title)

        # first, handle all of the regular datasets
        sample_names = sorted(config['riboseq_samples'].keys())
        
        # and check if we also have replicates
        if 'riboseq_biological_replicates' not in config:
            replicate_names = []
        else:
            replicate_names = sorted(ribo_utils.get_riboseq_replicates(config).keys())

        strands = ["+", "-"]


        i = 0
        for sample_name in sample_names:
            
            try:
                lengths, offsets = ribo_utils.get_periodic_lengths_and_offsets(config, sample_name)
            except FileNotFoundError:
                msg = "Could not parse out lengths and offsets for sample: {}. Skipping".format(sample_name)
                logger.error(msg)
                continue
            
            caption = "ORF types: {}".format(sample_name)

            # first, just dump all of the pie charts to the page
            
            
            for is_grouped in [True, False]:
                for is_chisq in chisq_values:
                    for is_filtered in [True, False]:

                        if is_chisq:
                            f = None
                            rw = None
                        else:
                            f = fraction
                            rw = reweighting_iterations
                        
                        orf_types_pie_chart = filenames.get_orf_types_pie_chart(
                            config['riboseq_data'], sample_name, length=lengths, offset=offsets, 
                            is_unique=True, note=out_note_str, image_type=args.image_type,
                            fraction=f, reweighting_iterations=rw,
                            is_grouped=is_grouped, is_chisq=is_chisq, is_filtered=is_filtered)

                        msg = "looking for image file: {}".format(orf_types_pie_chart)
                        logger.debug(msg)

                        if os.path.exists(orf_types_pie_chart):
                            if i%4 == 0:
                                latex.begin_figure(out)
                            
                            i += 1
                            latex.write_graphics(out, orf_types_pie_chart, height=0.23)

                            if i%4 == 0:
                                latex.write_caption(out, caption)
                                latex.end_figure(out)
                                latex.clearpage(out)



            if (i > 0) and (i%4) != 0:
                latex.write_caption(out, caption)
                latex.end_figure(out)
                latex.clearpage(out)

    
        i = 0
        # now, if the config file specifies replicates, create figures for those                
        for replicate_name in replicate_names:
            lengths = None
            offsets = None

            caption = "ORF types: {}".format(replicate_name)

            for is_grouped in [True, False]:
                for is_chisq in chisq_values:
                    for is_filtered in [True, False]:

                        if is_chisq:
                            f = None
                            rw = None
                        else:
                            f = fraction
                            rw = reweighting_iterations

                        
                        orf_types_pie_chart = filenames.get_orf_types_pie_chart(
                            config['riboseq_data'], replicate_name, length=lengths, offset=offsets, 
                            is_unique=True, note=out_note_str, image_type=args.image_type,
                            fraction=f, reweighting_iterations=rw,
                            is_grouped=is_grouped, is_chisq=is_chisq, is_filtered=is_filtered)

                        
                        msg = "looking for image file: {}".format(orf_types_pie_chart)
                        logger.debug(msg)

                        
                        if os.path.exists(orf_types_pie_chart):
                            if i%4 == 0:
                                latex.begin_figure(out)
                            
                            i += 1
                            latex.write_graphics(out, orf_types_pie_chart, height=0.23)

                            if i%4 == 0:
                                latex.write_caption(out, caption)
                                latex.end_figure(out)
                                latex.clearpage(out)



            if (i > 0) and (i%4) != 0:
                latex.write_caption(out, caption)
                latex.end_figure(out)
                latex.clearpage(out)


        ### ORF type length distributions
        title = "Predicted ORF type length distributions"
        latex.section(out, title)

        i = 0
        for sample_name in sample_names:
            
            try:
                lengths, offsets = ribo_utils.get_periodic_lengths_and_offsets(config, sample_name)
            except FileNotFoundError:
                msg = "Could not parse out lengths and offsets for sample: {}. Skipping".format(sample_name)
                logger.error(msg)
                continue
            
            caption = "ORF type length distributions: {}".format(sample_name)
            
            for is_grouped in [True, False]:
                for is_chisq in chisq_values:

                    if is_chisq:
                        f = None
                        rw = None
                    else:
                        f = fraction
                        rw = reweighting_iterations

                    orf_length_line_graph = filenames.get_orf_length_distribution_line_graph(
                        config['riboseq_data'], sample_name, length=lengths, offset=offsets, 
                        is_unique=True, note=out_note_str, image_type=args.image_type,
                        fraction=f, reweighting_iterations=rw,
                        is_grouped=is_grouped, is_chisq=is_chisq)

                    if os.path.exists(orf_length_line_graph):
                
                        if i%4 == 0:
                            latex.begin_figure(out)
                        
                        i += 1
                        latex.write_graphics(out, orf_length_line_graph, height=0.23)

                        if i%4 == 0:
                            latex.write_caption(out, caption)
                            latex.end_figure(out)
                            latex.clearpage(out)



            if (i > 0) and (i%4) != 0:
                latex.write_caption(out, caption)
                latex.end_figure(out)
                latex.clearpage(out)

        # now, if the config file specifies replicates, create figures for those  
        i = 0
        for replicate_name in replicate_names:
            lengths = None
            offsets = None

            caption = "ORF types: {}".format(replicate_name)
            
            for is_grouped in [True, False]:
                for is_chisq in chisq_values:

                    if is_chisq:
                        f = None
                        rw = None
                    else:
                        f = fraction
                        rw = reweighting_iterations

                    orf_length_line_graph = filenames.get_orf_length_distribution_line_graph(
                        config['riboseq_data'], replicate_name, length=lengths, offset=offsets, 
                        is_unique=True, note=out_note_str, image_type=args.image_type,
                        fraction=f, reweighting_iterations=rw,
                        is_grouped=is_grouped, is_chisq=is_chisq)
                    
                    if os.path.exists(orf_length_line_graph):
                
                        if i%4 == 0:
                            latex.begin_figure(out)
                        
                        i += 1
                        latex.write_graphics(out, orf_length_line_graph, height=0.23)

                        if i%4 == 0:
                            latex.write_caption(out, caption)
                            latex.end_figure(out)
                            latex.clearpage(out)



            if (i > 0) and (i%4) != 0:
                latex.write_caption(out, caption)
                latex.end_figure(out)
                latex.clearpage(out)

        ### ORF type metagene profiles
        title = "Predicted ORF type metagene profiles"
        latex.section(out, title)
        
        i = 0
        for sample_name in sample_names:
            
            try:
                lengths, offsets = ribo_utils.get_periodic_lengths_and_offsets(config, sample_name)
            except FileNotFoundError:
                msg = "Could not parse out lengths and offsets for sample: {}. Skipping".format(sample_name)
                logger.error(msg)
                continue
            
            caption = "ORF type metagene profiles: {}".format(sample_name)


            for is_chisq in chisq_values:

                if is_chisq:
                    f = None
                    rw = None
                else:
                    f = fraction
                    rw = reweighting_iterations

                orf_type_profile_base = filenames.get_orf_type_profile_base(
                    config['riboseq_data'], sample_name, length=lengths, offset=offsets, 
                    is_unique=True, note=out_note_str,
                    fraction=f, reweighting_iterations=rw,
                    is_chisq=is_chisq)

                for orf_type in ribo_utils.orf_types:
                    for strand in strands:
                        orf_type_profile = filenames.get_orf_type_profile_image(orf_type_profile_base, 
                            orf_type, strand, args.image_type)


                        msg = "Looking for image file: {}".format(orf_type_profile)
                        logger.debug(msg)
                        if os.path.exists(orf_type_profile):

                            if i%4 == 0:
                                latex.begin_figure(out)

                            i += 1
                            latex.write_graphics(out, orf_type_profile, height=0.23)

                            if i%4 == 0:
                                latex.write_caption(out, caption)
                                latex.end_figure(out)
                                latex.clearpage(out)

        if (i > 0) and (i%4 != 0):
            latex.write_caption(out, caption)
            latex.end_figure(out)
            latex.clearpage(out)

        i = 0
        for replicate_name in replicate_names:
            lengths = None
            offsets = None
                        
            caption = "ORF type metagene profiles: {}".format(replicate_name)
            for is_chisq in chisq_values:

                if is_chisq:
                    f = None
                    rw = None
                else:
                    f = fraction
                    rw = reweighting_iterations

                orf_type_profile_base = filenames.get_orf_type_profile_base(
                    config['riboseq_data'], replicate_name, length=lengths, offset=offsets, 
                    is_unique=True, note=out_note_str, 
                    fraction=f, reweighting_iterations=rw,
                    is_chisq=is_chisq)

                
                for orf_type in ribo_utils.orf_types:
                    for strand in strands:
                        orf_type_profile = filenames.get_orf_type_profile_image(orf_type_profile_base, 
                            orf_type, strand, args.image_type)

                        if os.path.exists(orf_type_profile):

                            if i%4 == 0:
                                latex.begin_figure(out)

                            i += 1
                            latex.write_graphics(out, orf_type_profile, height=0.23)

                            if i % 4 == 0:
                                latex.write_caption(out, caption)
                                latex.end_figure(out)
                                latex.clearpage(out)

            
        if (i > 0) and (i%4 != 0):
            latex.write_caption(out, caption)
            latex.end_figure(out)
            latex.clearpage(out)

        ### RPKM-BF scatter plots
        title = "RPKMs vs. Bayes factors"
        latex.section(out, title)

        i = 0
        for sample_name in sample_names:
            
            try:
                lengths, offsets = ribo_utils.get_periodic_lengths_and_offsets(config, sample_name)
            except FileNotFoundError:
                msg = "Could not parse out lengths and offsets for sample: {}. Skipping".format(sample_name)
                logger.error(msg)
                continue
            
            bf_rpkm_scatter_plot = filenames.get_bf_rpkm_scatter_plot(config['riboseq_data'], sample_name, 
                length=lengths, offset=offsets, 
                is_unique=True, note=out_note_str, image_type=args.image_type,
                is_smooth=True, fraction=fraction, reweighting_iterations=reweighting_iterations)

            if os.path.exists(bf_rpkm_scatter_plot):
                if i%4 == 0:
                    latex.begin_figure(out)
                    
                i += 1
                latex.write_graphics(out, bf_rpkm_scatter_plot, height=0.23)

                if i % 4 == 0:
                    latex.end_figure(out)
                    latex.clearpage(out)
            
        if (i > 0) and (i%4 != 0):
            latex.end_figure(out)
            latex.clearpage(out)

        # now, if the config file specifies replicates, create figures for those                
        for replicate_name in replicate_names:
            lengths = None
            offsets = None

            bf_rpkm_scatter_plot = filenames.get_bf_rpkm_scatter_plot(config['riboseq_data'], replicate_name, 
                length=lengths, offset=offsets, 
                is_unique=True, note=out_note_str, image_type=args.image_type,
                is_smooth=True, fraction=fraction, reweighting_iterations=reweighting_iterations)

            if os.path.exists(bf_rpkm_scatter_plot):
                if i%4 == 0:
                    latex.begin_figure(out)
                    
                i += 1
                latex.write_graphics(out, bf_rpkm_scatter_plot, height=0.23)

                if i % 4 == 0:
                    latex.end_figure(out)
                    latex.clearpage(out)
            
        if (i > 0) and (i%4 != 0):
            latex.end_figure(out)
            latex.clearpage(out)

        out.write(footer)

    
    os.chdir(args.out)
    cmd = "pdflatex -shell-escape prediction-report"
    utils.check_call(cmd)
    utils.check_call(cmd) # call again to fix references


if __name__ == '__main__':
    main()
