import smtplib
import ssl
import certifi
import html
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings
from app.schemas.contact import ContactRequest, AIAnalysis

logger = logging.getLogger(__name__)

_SENTIMENT_EMOJI = {"positive": "😊", "neutral": "😐", "negative": "😟"}
_CATEGORY_RU = {
    "project_inquiry": "Запрос на проект",
    "job_offer": "Предложение о работе",
    "consultation": "Консультация",
    "other": "Другое",
}


class EmailService:
    """Sends email notifications via mail.ru SMTP (SSL, port 465)."""

    def __init__(self) -> None:
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._user = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._owner = settings.OWNER_EMAIL

    def _send(self, msg: MIMEMultipart) -> None:
        context = ssl.create_default_context(cafile=certifi.where())
        with smtplib.SMTP_SSL(self._host, self._port, context=context, timeout=10) as server:
            server.login(self._user, self._password)
            server.send_message(msg)

    def send_notifications(
        self, data: ContactRequest, ai: AIAnalysis, request_id: str
    ) -> None:
        """Send owner + user emails in a single SMTP session."""
        owner_msg = self._build_owner_message(data, ai, request_id)
        user_msg = self._build_user_message(data, ai, request_id)

        context = ssl.create_default_context(cafile=certifi.where())
        with smtplib.SMTP_SSL(self._host, self._port, context=context, timeout=10) as server:
            server.login(self._user, self._password)
            server.send_message(owner_msg)
            server.send_message(user_msg)

        logger.info("Owner + user emails sent for request %s", request_id)

    def _build_owner_message(
        self, data: ContactRequest, ai: AIAnalysis, request_id: str
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 Новое обращение от {data.name}"
        msg["From"] = self._user
        msg["To"] = self._owner

        html = f"""<!DOCTYPE html>
<html lang="ru"><body style="margin:0;padding:0;background:#f4f4f7;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:30px 20px;">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <!-- Header -->
      <tr><td style="background:#1a1d27;padding:24px 32px;">
        <h2 style="margin:0;color:#fff;font-size:20px;">🔔 Новое обращение</h2>
        <p style="margin:6px 0 0;color:#8b8fa8;font-size:13px;">ID: {request_id}</p>
      </td></tr>
      <!-- Body -->
      <tr><td style="padding:28px 32px;">
        <table width="100%" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
          <tr style="border-bottom:1px solid #f0f0f0;">
            <td style="font-weight:600;color:#555;width:30%;vertical-align:top;">Имя</td>
            <td style="color:#222;">{data.name}</td>
          </tr>
          <tr style="border-bottom:1px solid #f0f0f0;background:#fafafa;">
            <td style="font-weight:600;color:#555;vertical-align:top;">Телефон</td>
            <td style="color:#222;">{data.phone}</td>
          </tr>
          <tr style="border-bottom:1px solid #f0f0f0;">
            <td style="font-weight:600;color:#555;vertical-align:top;">Email</td>
            <td><a href="mailto:{data.email}" style="color:#5b7cf0;">{data.email}</a></td>
          </tr>
          <tr>
            <td style="font-weight:600;color:#555;vertical-align:top;">Сообщение</td>
            <td style="color:#333;line-height:1.6;">{data.comment}</td>
          </tr>
        </table>
        <!-- AI Block -->
        <div style="margin-top:24px;padding:20px;background:#f7f8ff;border-radius:8px;border-left:4px solid #5b7cf0;">
          <h3 style="margin:0 0 12px;color:#1a1d27;font-size:15px;">🤖 AI-анализ</h3>
          <p style="margin:4px 0;color:#444;">
            <b>Тональность:</b> {_SENTIMENT_EMOJI.get(ai.sentiment, '❓')} {ai.sentiment}
          </p>
          <p style="margin:4px 0;color:#444;">
            <b>Категория:</b> {_CATEGORY_RU.get(ai.category, 'Другое')}
          </p>
          <p style="margin:12px 0 4px;color:#444;"><b>Предложенный ответ:</b></p>
          <p style="margin:0;color:#555;font-style:italic;line-height:1.6;">{ai.auto_reply}</p>
          {"" if ai.ai_available else '<p style="margin-top:8px;color:#e05050;font-size:12px;">⚠ AI-анализ недоступен, использован fallback</p>'}
        </div>
        <p style="margin-top:20px;color:#aaa;font-size:12px;">
          Получено: {datetime.now().strftime("%d.%m.%Y в %H:%M")}
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""

        msg.attach(MIMEText(html, "html", "utf-8"))
        return msg

    def _build_user_message(
        self, data: ContactRequest, ai: AIAnalysis, request_id: str
    ) -> MIMEMultipart:
        """Build a personalised confirmation for the user."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Получил ваше сообщение — Артём Hernandez"
        msg["From"] = self._user
        msg["To"] = data.email

        safe_name = html.escape(data.name)
        safe_comment = html.escape(data.comment).replace("\n", "<br>")
        safe_reply = html.escape(ai.auto_reply).replace("\n", "<br>")
        ai_note = (
            ""
            if ai.ai_available
            else '<p style="margin:8px 0 0;color:#e05050;font-size:12px;">⚠ AI был недоступен — ниже стандартный ответ</p>'
        )

        html_body = f"""<!DOCTYPE html>
<html lang="ru"><body style="margin:0;padding:0;background:#f4f4f7;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:30px 20px;">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <!-- Header -->
      <tr><td style="background:linear-gradient(135deg,#1a1d27,#2a2f45);padding:32px;text-align:center;">
        <h1 style="margin:0;color:#fff;font-size:22px;font-weight:600;">Артём Hernandez</h1>
        <p style="margin:6px 0 0;color:#8b8fa8;font-size:14px;">Backend Developer</p>
      </td></tr>
      <!-- Body -->
      <tr><td style="padding:32px;">
        <h2 style="margin:0 0 16px;color:#1a1d27;font-size:18px;">Привет, {safe_name}!</h2>
        <p style="margin:0 0 24px;color:#555;line-height:1.6;font-size:14px;">
          Спасибо за обращение. Ниже — копия вашего сообщения и предложенный ответ.
        </p>

        <div style="margin-bottom:20px;padding:18px;background:#fafafa;border-radius:8px;border-left:4px solid #1e3b7b;">
          <p style="margin:0 0 10px;color:#1a1d27;font-size:14px;font-weight:600;">Ваше сообщение</p>
          <p style="margin:0;color:#444;line-height:1.7;font-size:15px;">{safe_comment}</p>
        </div>

        <div style="margin-bottom:24px;padding:18px;background:#f7f8ff;border-radius:8px;border-left:4px solid #0072c6;">
          <p style="margin:0 0 10px;color:#1a1d27;font-size:14px;font-weight:600;">Предложенный ответ</p>
          <p style="margin:0;color:#444;line-height:1.7;font-size:15px;font-style:italic;">{safe_reply}</p>
          {ai_note}
        </div>

        <div style="padding:16px;background:#f7f8ff;border-radius:8px;border-left:3px solid #5b7cf0;">
          <p style="margin:0;color:#666;font-size:13px;line-height:1.5;">
            Обращение #{request_id[:8].upper()} зарегистрировано {datetime.now().strftime("%d.%m.%Y")}.
            <br>Если что-то срочное — пишите напрямую на {self._owner}.
          </p>
        </div>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""

        msg.attach(MIMEText(html_body, "html", "utf-8"))
        return msg

    def send_owner_notification(
        self, data: ContactRequest, ai: AIAnalysis, request_id: str
    ) -> None:
        self._send(self._build_owner_message(data, ai, request_id))
        logger.info("Owner notification sent for request %s", request_id)

    def send_user_confirmation(
        self, data: ContactRequest, ai: AIAnalysis, request_id: str
    ) -> None:
        self._send(self._build_user_message(data, ai, request_id))
        logger.info("User confirmation sent to %s for request %s", data.email, request_id)

    def check_connection(self) -> bool:
        """Ping SMTP to verify credentials work."""
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            with smtplib.SMTP_SSL(self._host, self._port, context=context, timeout=5) as server:
                server.login(self._user, self._password)
            return True
        except Exception as e:
            logger.warning("SMTP health check failed: %s", e)
            return False
