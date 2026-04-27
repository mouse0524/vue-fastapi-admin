import random
import smtplib
import time
from email.mime.text import MIMEText
from email.utils import formataddr

from fastapi import HTTPException

from app.core.redis_client import execute_redis
from app.models.admin import SystemSetting
from app.settings import settings


_LOCAL_EMAIL_CODE_CACHE: dict[str, dict] = {}


class MailController:
    @staticmethod
    def _gen_code(length: int = 6) -> str:
        return "".join(str(random.randint(0, 9)) for _ in range(length))

    @staticmethod
    async def _get_setting() -> SystemSetting:
        setting = await SystemSetting.first()
        if not setting:
            setting = await SystemSetting.create()
        return setting

    @staticmethod
    def _render_template(template: str, params: dict) -> str:
        content = template or ""
        for key, value in params.items():
            content = content.replace("{" + key + "}", str(value if value is not None else ""))
        return content

    @staticmethod
    def _register_type_label(register_type: str) -> str:
        return "渠道商" if register_type == "channel" else "用户"

    async def _send_email(self, *, to_email: str, subject: str, content: str, is_html: bool = False) -> None:
        setting = await self._get_setting()
        if not setting.smtp_host or not setting.smtp_sender:
            raise HTTPException(status_code=400, detail="系统未配置发件箱")

        msg = MIMEText(content, "html" if is_html else "plain", "utf-8")
        msg["From"] = formataddr((setting.smtp_sender_name or "系统通知", setting.smtp_sender))
        msg["To"] = to_email
        msg["Subject"] = subject

        username = setting.smtp_username or setting.smtp_sender
        try:
            if setting.smtp_use_ssl:
                server = smtplib.SMTP_SSL(setting.smtp_host, setting.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(setting.smtp_host, setting.smtp_port, timeout=10)
            if setting.smtp_use_tls and not setting.smtp_use_ssl:
                server.starttls()
            if username and setting.smtp_password:
                server.login(username, setting.smtp_password)
            server.sendmail(setting.smtp_sender, [to_email], msg.as_string())
            server.quit()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"发送邮件失败: {exc}")

    @staticmethod
    def _cleanup_local_cache() -> None:
        now = time.time()
        expired_keys = [k for k, v in _LOCAL_EMAIL_CODE_CACHE.items() if v.get("expires_at", 0) <= now]
        for key in expired_keys:
            _LOCAL_EMAIL_CODE_CACHE.pop(key, None)

    @staticmethod
    def _set_local_code(email: str, code: str) -> None:
        MailController._cleanup_local_cache()
        key = email.lower().strip()
        _LOCAL_EMAIL_CODE_CACHE[key] = {
            "code": code.strip(),
            "expires_at": time.time() + settings.EMAIL_VERIFY_TTL_SECONDS,
        }

    @staticmethod
    def _verify_local_code(email: str, code: str) -> bool:
        MailController._cleanup_local_cache()
        key = email.lower().strip()
        item = _LOCAL_EMAIL_CODE_CACHE.get(key)
        if not item:
            return False
        is_valid = item.get("code") == code.strip()
        if is_valid:
            _LOCAL_EMAIL_CODE_CACHE.pop(key, None)
        return is_valid

    @staticmethod
    def _normalize_code(code) -> str:
        if code is None:
            return ""
        if isinstance(code, bytes):
            code = code.decode("utf-8")
        return str(code).strip()

    async def send_partner_verify_code(self, email: str) -> None:
        setting = await self._get_setting()

        code = self._gen_code()
        minutes = max(settings.EMAIL_VERIFY_TTL_SECONDS // 60, 1)
        content = (setting.email_verify_template or "您好，您的验证码是：{code}，{minutes}分钟内有效。").format(
            code=code,
            minutes=minutes,
        )
        subject = setting.email_verify_subject or "代理商注册验证码"

        await self._send_email(
            to_email=email,
            subject=subject,
            content=content,
            is_html=bool(getattr(setting, "email_verify_is_html", False)),
        )

        self._set_local_code(email, code)
        try:
            await execute_redis(
                "setex", f"email_verify:{email.lower().strip()}", settings.EMAIL_VERIFY_TTL_SECONDS, code
            )
        except Exception:
            pass

    async def verify_email_code(self, email: str, code: str) -> bool:
        key = f"email_verify:{email.lower().strip()}"
        try:
            saved = await execute_redis("get", key)
            if not saved:
                return self._verify_local_code(email, code)
            if self._normalize_code(saved) == self._normalize_code(code):
                await execute_redis("delete", key)
                _LOCAL_EMAIL_CODE_CACHE.pop(email.lower().strip(), None)
                return True
            return False
        except Exception:
            return self._verify_local_code(email, code)

    async def send_register_review_notice(
        self,
        *,
        to_email: str,
        contact_name: str,
        register_type: str,
        approved: bool,
        reason: str | None = None,
    ) -> None:
        setting = await self._get_setting()
        register_type_text = self._register_type_label(register_type)

        if approved:
            subject = setting.register_review_approve_subject or "注册审核结果通知"
            template = (
                setting.register_review_approve_template
                or "您好，{contact_name}，您的{register_type}注册申请已审核通过，现可使用邮箱登录系统。"
            )
            is_html = bool(getattr(setting, "register_review_approve_is_html", False))
        else:
            subject = setting.register_review_reject_subject or "注册审核结果通知"
            template = (
                setting.register_review_reject_template
                or "您好，{contact_name}，您的{register_type}注册申请已驳回。驳回理由：{reason}"
            )
            is_html = bool(getattr(setting, "register_review_reject_is_html", False))

        content = self._render_template(
            template,
            {
                "contact_name": contact_name,
                "register_type": register_type_text,
                "reason": reason or "无",
            },
        )
        await self._send_email(to_email=to_email, subject=subject, content=content, is_html=is_html)


mail_controller = MailController()
