import pathlib

from jinja2 import Environment, FileSystemLoader, select_autoescape
from .jinja_template_filters import no_filters, convert_sex


template_env = Environment(loader=FileSystemLoader(
    pathlib.Path.cwd() / 'balance_bot' / 'templates',
    ),
    autoescape=select_autoescape(['html']),
    enable_async=True,
)

template_env.filters['no_filter'] = no_filters
template_env.filters['convert_sex'] = convert_sex


async def render_template(template_name: str, **context) -> str:

    template = template_env.get_template(template_name)

    return await template.render_async(context)
