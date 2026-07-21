import os
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

from d1 import D1Error, d1_execute, d1_query

# -------------------------
# Configuration
# -------------------------
# Fail fast and loudly instead of silently accepting payments to a placeholder
# wallet or letting a missing D1 credential surface as a 500 on first request.
PAY_TO = os.environ["PAY_TO"]  # e.g. "0xAbC123...", your real Base wallet
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]  # shared secret for the review endpoints
NETWORK = Network.BASE if os.environ.get("X402_NETWORK") == "mainnet" else Network.BASE_SEPOLIA
PRICE = os.environ.get("GUEST_POST_PRICE", "$5.00")

app = FastAPI(title="Trovit Guest Posts")

# -------------------------
# x402
# -------------------------
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url="https://x402.org/facilitator"))
server = x402ResourceServer(facilitator)
server.register(NETWORK, ExactEvmServerScheme())

app.add_middleware(
    PaymentMiddlewareASGI,
    server=server,
    routes=[
        RouteConfig(
            path="/guest-post",
            method="POST",
            payment_options=[
                PaymentOption(
                    price=PRICE,
                    network=NETWORK,
                    pay_to=PAY_TO,
                    description="Guest Post Submission",
                )
            ],
        )
    ],
)


# -------------------------
# Models
# -------------------------
class GuestPost(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=200, max_length=20000)
    author: str = Field(..., min_length=2, max_length=100)
    canonical_url: HttpUrl | None = None


class SubmissionOut(BaseModel):
    id: str
    title: str
    author: str
    canonical_url: str | None
    status: str
    created_at: str
    updated_at: str


class StatusUpdate(BaseModel):
    status: Literal["approved", "rejected", "pending_review"]


# -------------------------
# Admin auth
# -------------------------
def require_admin(x_admin_token: str = Header(...)) -> None:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


# -------------------------
# Public endpoint (paid)
# -------------------------
@app.post("/guest-post")
async def guest_post(post: GuestPost):
    post_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # NOTE: if your x402 middleware version exposes payment details on the
    # request/response (payer address, tx hash), read them here and pass
    # them into the INSERT below instead of leaving them NULL. The exact
    # attribute depends on your x402-http version, so check its docs/source
    # for what the middleware attaches after a settled payment.

    try:
        await d1_execute(
            """
            INSERT INTO submissions
                (id, title, content, author, canonical_url, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending_review', ?, ?)
            """,
            [
                post_id,
                post.title,
                post.content,
                post.author,
                str(post.canonical_url) if post.canonical_url else None,
                now,
                now,
            ],
        )
    except D1Error as exc:
        # The payment has already been captured by the middleware at this point,
        # so a storage failure here needs to be visible/loggable, not swallowed.
        raise HTTPException(status_code=502, detail=f"Storage error: {exc}") from exc

    return {"success": True, "submission_id": post_id, "status": "pending_review"}


# -------------------------
# Admin endpoints (free, token-gated)
# -------------------------
@app.get("/submissions", response_model=list[SubmissionOut], dependencies=[Depends(require_admin)])
async def list_submissions(
    status: Literal["pending_review", "approved", "rejected"] | None = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    if status:
        rows = await d1_query(
            "SELECT id, title, author, canonical_url, status, created_at, updated_at "
            "FROM submissions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            [status, limit],
        )
    else:
        rows = await d1_query(
            "SELECT id, title, author, canonical_url, status, created_at, updated_at "
            "FROM submissions ORDER BY created_at DESC LIMIT ?",
            [limit],
        )
    return rows


@app.get("/submissions/{submission_id}", dependencies=[Depends(require_admin)])
async def get_submission(submission_id: str):
    rows = await d1_query("SELECT * FROM submissions WHERE id = ?", [submission_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Submission not found")
    return rows[0]


@app.patch("/submissions/{submission_id}", dependencies=[Depends(require_admin)])
async def update_submission_status(submission_id: str, update: StatusUpdate):
    now = datetime.now(timezone.utc).isoformat()
    rows = await d1_query("SELECT id FROM submissions WHERE id = ?", [submission_id])
    if not rows:
        raise HTTPException(status_code=404, detail="Submission not found")

    await d1_execute(
        "UPDATE submissions SET status = ?, updated_at = ? WHERE id = ?",
        [update.status, now, submission_id],
    )
    return {"success": True, "id": submission_id, "status": update.status}


@app.get("/")
async def root():
    return {"service": "Trovit Guest Posts API", "x402": True, "network": NETWORK.value}
