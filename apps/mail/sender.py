import aiosmtplib
from email.message import EmailMessage

from conf import bot_settings
from utils.jinja_template import render_template


async def send_email(
        recipients: list[str],
        theme: str,
        msg: str,
        **kwargs,
):

    template_name = kwargs.get('template_name')
    context = kwargs.get('context')

    message = EmailMessage()
    message.set_content(msg)

    if template_name:
        html = await render_template(
            template_name,
            context=context,
        )

        message.add_alternative(html, subtype='html')

    message['Subject'] = theme
    message['From'] = bot_settings.email_username.get_secret_value()
    message['To'] = ', '.join(recipients)

    smtp = aiosmtplib.SMTP(
        hostname=bot_settings.smtp_host.get_secret_value(),
        port=bot_settings.smtp_port.get_secret_value(),
        start_tls=True,
    )

    await smtp.connect()
    await smtp.login(
        bot_settings.email_username.get_secret_value(),
        bot_settings.email_password.get_secret_value(),
    )

    try:
        await smtp.send_message(message)
    except Exception as e:
        print(e)
    finally:
        smtp.close()