# calling the pipeline
nextflow run nf-core/rnaseq -r 3.24.0 \
    --custom_config_base ${CUSTOM_CONFIG_BASE} \
    -config ${CUSTOM_CONFIG_BASE}/nfcore_custom.config \
    -config ${CUSTOM_CONFIG_BASE}/pipeline/rnaseq.config \
    -config conf/custom-{{ cookiecutter.__pipeline }}.config -profile ibba,galileo \
    -resume -params-file conf/params-{{ cookiecutter.__pipeline }}.json
