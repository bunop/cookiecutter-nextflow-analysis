# calling the pipeline
nextflow run nf-core/methylseq -r 4.2.0 \
    --custom_config_base ${CUSTOM_CONFIG_BASE} \
    -config ${CUSTOM_CONFIG_BASE}/nfcore_custom-{{ cookiecutter.__pipeline }}.config \
    -config ${CUSTOM_CONFIG_BASE}/pipeline/methylseq.config \
    -config conf/custom-{{ cookiecutter.__pipeline }}.config -profile ibba,galileo \
    -resume -params-file conf/params-{{ cookiecutter.__pipeline }}.json