# {{ cookiecutter.project_slug }}

{% if cookiecutter.project_type == "wf-basecalling" %}
{% include "README/basecalling.jinja" %}
{% else %}
Few lines about the project.
{% endif %}
