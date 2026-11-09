# pin the nextflow version to 25.10.9 to avoid issues with the latest version
# (container download, issues with config parsing, etc.)
export NXF_VER="${NXF_VER:-25.10.9}"

# calling the pipeline
nextflow run nf-core/methylseq -r 4.2.0 \
    --custom_config_base ${CUSTOM_CONFIG_BASE} \
    -config ${CUSTOM_CONFIG_BASE}/nfcore_custom.config \
    -config ${CUSTOM_CONFIG_BASE}/pipeline/methylseq.config \
    -config conf/custom-{{ cookiecutter.__pipeline }}.config -profile ibba,galileo \
    -resume -params-file conf/params-{{ cookiecutter.__pipeline }}.json
