from setuptools import find_packages, setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop

import importlib
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

###
#   If you receive an error like: NameError: name 'install' is not defined
#   Please make sure the most recent version of pip is installed
###

###
#   Most of this is taken from a template at:
#       http://diffbrent.ghost.io/correctly-adding-nltk-to-your-python-package-using-setup-py-post-install-commands/
###

preprocessing_scripts = [
    'extract-orf-coordinates=rpbp.reference_preprocessing.extract_orf_coordinates:main',
    'label-orfs=rpbp.reference_preprocessing.label_orfs:main',
    'prepare-rpbp-genome=rpbp.reference_preprocessing.prepare_rpbp_genome:main'
]

profile_construction_scripts = [
    'create-orf-profiles=rpbp.orf_profile_construction.create_orf_profiles:main',
    'create-base-genome-profile=rpbp.orf_profile_construction.create_base_genome_profile:main',
    'extract-orf-profiles=rpbp.orf_profile_construction.extract_orf_profiles:main',
    'merge-replicate-orf-profiles=rpbp.translation_prediction.merge_replicate_orf_profiles:main',
    'run-rpbp-pipeline=rpbp.run_rpbp_pipeline:main',
    'run-all-rpbp-instances=rpbp.run_all_rpbp_instances:main',
]

translation_prediction_scripts = [
    'predict-translated-orfs=rpbp.translation_prediction.predict_translated_orfs:main',
    'estimate-orf-bayes-factors=rpbp.translation_prediction.estimate_orf_bayes_factors:main',
    'select-final-prediction-set=rpbp.translation_prediction.select_final_prediction_set:main'
]

preprocessing_report_scripts = [
    'create-read-length-metagene-profile-plot=rpbp.analysis.profile_construction.create_read_length_metagene_profile_plot:main',
    'visualize-metagene-profile-bayes-factor=rpbp.analysis.profile_construction.visualize_metagene_profile_bayes_factor:main',
    'create-rpbp-preprocessing-report=rpbp.analysis.profile_construction.create_rpbp_preprocessing_report:main',
    'get-all-read-filtering-counts=rpbp.analysis.profile_construction.get_all_read_filtering_counts:main',
    'visualize-read-filtering-counts=rpbp.analysis.profile_construction.visualize_read_filtering_counts:main'
]

predictions_report_scripts = [
    'visualize-orf-type-metagene-profiles=rpbp.analysis.rpbp_predictions.visualize_orf_type_metagene_profiles:main',
    'create-orf-types-pie-chart=rpbp.analysis.rpbp_predictions.create_orf_types_pie_chart:main',
    'create-orf-types-bar-chart=rpbp.analysis.rpbp_predictions.create_orf_types_bar_chart:main',
    'create-orf-length-distribution-line-graph=rpbp.analysis.rpbp_predictions.create_orf_length_distribution_line_graph:main',
    'create-rpbp-predictions-report=rpbp.analysis.rpbp_predictions.create_rpbp_predictions_report:main',
    'create-bf-rpkm-scatter-plot=rpbp.analysis.rpbp_predictions.create_bf_rpkm_scatter_plot:main'
]

proteomics_report_scripts = [
    'get-orf-peptide-matches=rpbp.analysis.proteomics.get_orf_peptide_matches:main',
    'get-all-orf-peptide-matches=rpbp.analysis.proteomics.get_all_orf_peptide_matches:main',
    'create-orf-peptide-coverage-line-graph=rpbp.analysis.proteomics.create_orf_peptide_coverage_line_graph:main',
    'filter-nonunique-peptide-matches=rpbp.analysis.proteomics.filter_nonunique_peptide_matches:main',
    'create-proteomics-report=rpbp.analysis.proteomics.create_proteomics_report:main'
]

other_scripts = [
    'create-riboseq-test-dataset=rpbp.analysis.create_riboseq_test_dataset:main',
    'match-orfs-with-qti-seq-peaks=rpbp.analysis.qti_seq.match_orfs_with_qti_seq_peaks:main',
    'add-mygene-info-to-orfs=rpbp.analysis.rpbp_predictions.add_mygene_info_to_orfs:main',
    'find-differential-micropeptides=rpbp.analysis.find_differential_micropeptides:main',
    'cluster-subcodon-counts=rpbp.analysis.profile_construction.cluster_subcodon_counts:main',
    'visualize-subcodon-clusters=rpbp.analysis.profile_construction.visualize_subcodon_clusters:main',
    'create-read-length-orf-profiles=rpbp.analysis.profile_construction.create_read_length_orf_profiles:main',
    'collect-read-length-orf-profiles=rpbp.analysis.profile_construction.collect_read_length_orf_profiles:main'
]

console_scripts = (preprocessing_scripts + 
    profile_construction_scripts + 
    translation_prediction_scripts + 
    preprocessing_report_scripts + 
    proteomics_report_scripts + 
    predictions_report_scripts + 
    other_scripts
)

external_requirements =  [
    'cython',
    'numpy',
    'scipy',
    'pandas',
    'matplotlib',
    'matplotlib_venn',
    'seaborn',
    'joblib',
    'docopt',
    'tqdm',
    'statsmodels',
    'pysam',
    'pyfasta',
    'pystan==2.16.0.0',
    'pyyaml',
    'psutil',
    'biopython',
    'patsy', # used in statsmodels 
    'misc==0.2.5', # this has to be installed via requirements.txt
    'riboutils==0.2.5', # this, too,
    'bio-utils==0.2.4'  # and me!
]

stan_model_files = [
    os.path.join("nonperiodic", "no-periodicity.stan"),
    os.path.join("nonperiodic", "start-high-high-low.stan"),
    os.path.join("nonperiodic", "start-high-low-high.stan"),
    os.path.join("periodic", "start-high-low-low.stan"),
    os.path.join("untranslated", "gaussian-naive-bayes.stan"),
    os.path.join("translated", "periodic-gaussian-mixture.stan")
    #os.path.join("translated", "periodic-cauchy-mixture.stan"),
    #os.path.join("translated", "zero-inflated-periodic-cauchy-mixture.stan")
]

stan_pickle_files = [
    os.path.join("nonperiodic", "no-periodicity.pkl"),
    os.path.join("nonperiodic", "start-high-high-low.pkl"),
    os.path.join("nonperiodic", "start-high-low-high.pkl"),
    os.path.join("periodic", "start-high-low-low.pkl"),
    os.path.join("untranslated", "gaussian-naive-bayes.pkl"),
    os.path.join("translated", "periodic-gaussian-mixture.pkl")
    #os.path.join("translated", "periodic-cauchy-mixture.pkl"),
    #os.path.join("translated", "zero-inflated-periodic-cauchy-mixture.pkl")
]


def _post_install(self):
    import site
    importlib.reload(site)

    import shlex
    
    import riboutils.ribo_filenames as filenames
    import misc.utils as utils
    import misc.shell_utils as shell_utils
    
    smf = [os.path.join("rpbp_models", s) for s in stan_model_files]

    models_base = filenames.get_default_models_base()
    spf = [os.path.join(models_base, s) for s in stan_pickle_files]

    # compile and pickle the stans models
    for stan, pickle in zip(smf, spf):
        if os.path.exists(pickle):
            msg = "A model alread exists at: {}. Skipping.".format(pickle)
            logging.warning(msg)
            continue

        # make sure the path exists
        dirname = os.path.dirname(pickle)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        cmd = "pickle-stan {} {}".format(shlex.quote(stan), shlex.quote(pickle))
        logging.info(cmd)
        subprocess.call(cmd, shell=True)

    # check for the prerequisite programs
    programs = ['flexbar']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='flexbar', logger=logger)
        
    programs = ['STAR']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='STAR', logger=logger)

    programs = ['bowtie2', 'bowtie2-build-s']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='bowtie2', logger=logger)

    programs = ['samtools']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='SAMtools', logger=logger)

def install_requirements(is_user):
    # private dependencies are now specified with requirements.txt
    pass

class my_install(_install):
    def run(self):
        level = logging.getLevelName("INFO")
        logging.basicConfig(level=level,
            format='%(levelname)-8s : %(message)s')

        _install.run(self)
        install_requirements(self.user)
        _post_install(self)

class my_develop(_develop):  
    def run(self):
        level = logging.getLevelName("INFO")
        logging.basicConfig(level=level,
            format='%(levelname)-8s : %(message)s')

        _develop.run(self)
        install_requirements(self.user)
        _post_install(self)

def readme():
    with open('README.md') as f:
        return f.read()

def description():
    description=("This package contains the Rp-Bp pipeline for predicting "
        "translation of open reading frames from ribosome profiling data.")
    return description

setup(name='rpbp',
        version='1.1.11',
        description=description(),
        long_description=readme(),
        keywords="rpbp ribosome profiling bayesian inference markov chain monte carlo translation",
        url="",
        author="Brandon Malone",
        author_email="bmmalone@gmail.com",
        license='MIT',
        packages=find_packages(),
        install_requires = [external_requirements],
        cmdclass={'install': my_install,  # override install
                  'develop': my_develop   # develop is used for pip install -e .
        },  

        include_package_data=True,
        test_suite='nose.collector',
        tests_require=['nose'],
        entry_points = {
            'console_scripts': console_scripts
        },
        zip_safe=False
        )
