# calling the pipeline
nextflow run nf-core/smrnaseq -r 2.4.1 \
    --custom_config_base ${CUSTOM_CONFIG_BASE} \
    -config ${CUSTOM_CONFIG_BASE}/nfcore_custom.config \
    -config ${CUSTOM_CONFIG_BASE}/pipeline/smrnaseq.config \
    -config conf/custom.config -profile ibba,galileo \
    -resume -params-file conf/params.json
