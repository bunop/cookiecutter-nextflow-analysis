# mind to the pipeline version (required)
nextflow run bunop/wf-basecalling -r v1.5.9-mc \
    --custom_config_base ${CUSTOM_CONFIG_BASE} \
    -config ${CUSTOM_CONFIG_BASE}/nfcore_custom-{{ cookiecutter.__pipeline }}.config \
    -config ${CUSTOM_CONFIG_BASE}/pipeline/wf-basecalling.config \
    -config conf/custom-{{ cookiecutter.__pipeline }}.config -profile ibba,galileo,singularity \
    -resume -params-file conf/params-{{ cookiecutter.__pipeline }}.json
