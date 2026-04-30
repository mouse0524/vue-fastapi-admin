import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.tickets import tickets as tickets_module
from app.core.dependency import AuthControl


class TicketGetApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(tickets_module.router, prefix="/api/v1/tickets")

        async def _fake_auth():
            return SimpleNamespace(id=1)

        self.app.dependency_overrides[AuthControl.is_authed] = _fake_auth
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_get_ticket_forbidden(self):
        current_user = SimpleNamespace(id=10, is_superuser=False)
        ticket = SimpleNamespace(id=1001, submitter_id=11, tech_id=12, status="pending_review")

        with (
            patch.object(tickets_module, "_get_current_user", AsyncMock(return_value=current_user)),
            patch.object(tickets_module, "_get_user_role_names", AsyncMock(return_value=[])),
            patch.object(tickets_module.Ticket, "get", AsyncMock(return_value=ticket)),
        ):
            resp = self.client.get("/api/v1/tickets/get", params={"ticket_id": 1001})

        self.assertEqual(resp.status_code, 403)
        body = resp.json()
        self.assertEqual(body.get("code"), 403)

    def test_get_ticket_success_for_admin(self):
        current_user = SimpleNamespace(id=10, is_superuser=False)
        ticket = SimpleNamespace(id=1001, submitter_id=11, tech_id=12, status="done")
        detail = {"id": 1001, "title": "demo"}

        with (
            patch.object(tickets_module, "_get_current_user", AsyncMock(return_value=current_user)),
            patch.object(tickets_module, "_get_user_role_names", AsyncMock(return_value=["管理员"])),
            patch.object(tickets_module.Ticket, "get", AsyncMock(return_value=ticket)),
            patch.object(tickets_module.ticket_controller, "get_ticket_detail", AsyncMock(return_value=detail)),
        ):
            resp = self.client.get("/api/v1/tickets/get", params={"ticket_id": 1001})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("code"), 200)
        self.assertEqual(body.get("data", {}).get("id"), 1001)

    def test_list_ticket_for_tech_role_applies_scope_filter(self):
        current_user = SimpleNamespace(id=10, is_superuser=False)

        with (
            patch.object(tickets_module, "_get_current_user", AsyncMock(return_value=current_user)),
            patch.object(tickets_module, "_get_user_role_names", AsyncMock(return_value=["技术"])),
            patch.object(tickets_module.ticket_controller, "list_tickets", AsyncMock(return_value=(1, [{"id": 1}])) ) as mock_list,
        ):
            resp = self.client.get("/api/v1/tickets/list", params={"page": 1, "page_size": 10})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("code"), 200)
        self.assertEqual(body.get("total"), 1)

        call_kwargs = mock_list.await_args.kwargs
        self.assertEqual(call_kwargs.get("page"), 1)
        self.assertEqual(call_kwargs.get("page_size"), 10)

        search_q = call_kwargs.get("search")
        self.assertEqual(getattr(search_q, "join_type", ""), "AND")
        scope_q = search_q.children[-1]
        self.assertEqual(getattr(scope_q, "join_type", ""), "OR")
        self.assertEqual(scope_q.children[0].filters.get("tech_id"), 10)
        self.assertEqual(scope_q.children[1].filters.get("submitter_id"), 10)


if __name__ == "__main__":
    unittest.main()
