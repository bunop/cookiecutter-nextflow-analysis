# mind to the pipeline version (required)
nextflow run nf-core/methylong -r 1.0.0 \
    --custom_config_base ${CUSTOM_CONFIG_BASE} \
    -config ${CUSTOM_CONFIG_BASE}/nfcore_custom.config \
    -config ${CUSTOM_CONFIG_BASE}/pipeline/methylong.config \
    -config conf/custom.config -profile ibba,galileo \
    -resume -params-file conf/params.json