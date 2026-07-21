# Trovit Guest Posts API

A FastAPI-powered guest post submission service that integrates **x402 cryptocurrency payments** with **Cloudflare D1** database storage. Submit guest posts by making a payment, approve/reject submissions via admin APIs.

## Features

- 🔐 **Paid Submissions**: Accept guest posts only after x402 payment is processed
- 💾 **Cloudflare D1 Backend**: Serverless SQL database for submission storage
- 🛡️ **Admin Review Panel**: Token-gated endpoints to manage and moderate submissions
- ⛓️ **EVM-Native**: Built on the x402 framework with Base/Base Sepolia support
- 🚀 **Production-Ready**: Error handling, parameterized queries, and async/await support

## Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Database**: Cloudflare D1 (HTTP query API)
- **Payments**: x402 (cryptocurrency payment middleware)
- **Networks**: Base (mainnet) / Base Sepolia (testnet)
- **Language**: Python 3.9+

## Project Structure

```
├── main.py           # FastAPI app, routes, and x402 middleware
├── d1.py             # Cloudflare D1 HTTP client
├── schema.sql        # Database schema initialization
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Installation

### Prerequisites

- Python 3.9+
- Cloudflare account with D1 database
- x402 facilitator access (https://x402.org/facilitator)
- Base or Base Sepolia wallet address for payments

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/BesrourMS/guest-posts-x402.git
   cd guest-posts-x402
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export CF_ACCOUNT_ID="your_cloudflare_account_id"
   export CF_D1_DATABASE_ID="your_d1_database_id"
   export CF_API_TOKEN="your_cloudflare_api_token"
   export PAY_TO="0x..."  # Your wallet address on Base
   export ADMIN_TOKEN="your_secret_admin_token"
   export X402_NETWORK="mainnet"  # or omit for testnet (Base Sepolia)
   export GUEST_POST_PRICE="$5.00"  # Optional, defaults to $5.00
   ```

5. **Initialize the database**
   ```bash
   # Using wrangler CLI (if deployed on Cloudflare Workers)
   wrangler d1 execute <database-name> --file=schema.sql --remote
   
   # Or run via the D1 HTTP API directly
   ```

6. **Run the server**
   ```bash
   uvicorn main:app --reload
   ```

   API will be available at `http://localhost:8000`

## API Endpoints

### Public Endpoints

#### `POST /guest-post` (Paid)
Submit a guest post. Payment must be completed via x402 middleware before the submission is stored.

**Request Body:**
```json
{
  "title": "My Guest Post Title",
  "content": "Detailed content here (min 200 chars, max 20,000)",
  "author": "Author Name",
  "canonical_url": "https://example.com/original-post"  // optional
}
```

**Response (201):**
```json
{
  "success": true,
  "submission_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending_review"
}
```

**Cost**: Configurable via `GUEST_POST_PRICE` (default: $5.00)

#### `GET /` (Health Check)
Returns service info and network details.

**Response:**
```json
{
  "service": "Trovit Guest Posts API",
  "x402": true,
  "network": "Base"
}
```

### Admin Endpoints (Token-Gated)

All admin endpoints require the `X-Admin-Token` header:
```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" https://api.example.com/submissions
```

#### `GET /submissions` 
List all submissions, optionally filtered by status.

**Query Parameters:**
- `status` (optional): `pending_review`, `approved`, or `rejected`
- `limit` (optional, default: 50, max: 200): Number of results

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Guest Post Title",
    "author": "John Doe",
    "canonical_url": "https://example.com/post",
    "status": "pending_review",
    "created_at": "2026-01-15T10:30:00+00:00",
    "updated_at": "2026-01-15T10:30:00+00:00"
  }
]
```

#### `GET /submissions/{submission_id}`
Retrieve a single submission by ID.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Guest Post Title",
  "content": "Full content...",
  "author": "John Doe",
  "canonical_url": "https://example.com/post",
  "status": "pending_review",
  "payer_address": "0x...",
  "payment_tx_hash": "0x...",
  "created_at": "2026-01-15T10:30:00+00:00",
  "updated_at": "2026-01-15T10:30:00+00:00"
}
```

#### `PATCH /submissions/{submission_id}`
Update the status of a submission.

**Request Body:**
```json
{
  "status": "approved"  // or "rejected" or "pending_review"
}
```

**Response:**
```json
{
  "success": true,
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "approved"
}
```

## Database Schema

The D1 database includes a `submissions` table with the following structure:

| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT | Primary key (UUID) |
| `title` | TEXT | Post title (5-200 chars) |
| `content` | TEXT | Post content (200-20,000 chars) |
| `author` | TEXT | Author name (2-100 chars) |
| `canonical_url` | TEXT | Optional original URL |
| `status` | TEXT | `pending_review`, `approved`, or `rejected` |
| `payer_address` | TEXT | Wallet address that paid (for future use) |
| `payment_tx_hash` | TEXT | Transaction hash (for future use) |
| `created_at` | TEXT | ISO 8601 timestamp |
| `updated_at` | TEXT | ISO 8601 timestamp |

**Indexes:**
- `idx_submissions_status` on `status`
- `idx_submissions_created_at` on `created_at`

## Configuration

| Environment Variable | Required | Default | Description |
|----------------------|----------|---------|-------------|
| `CF_ACCOUNT_ID` | ✓ | — | Cloudflare account ID |
| `CF_D1_DATABASE_ID` | ✓ | — | D1 database ID |
| `CF_API_TOKEN` | ✓ | — | Cloudflare API token |
| `PAY_TO` | ✓ | — | Wallet address to receive payments |
| `ADMIN_TOKEN` | ✓ | — | Secret token for admin endpoints |
| `X402_NETWORK` | ✗ | `testnet` | Set to `mainnet` for Base mainnet |
| `GUEST_POST_PRICE` | ✗ | `$5.00` | Price per guest post submission |

## Payment Flow

1. **Client submits** a guest post via `POST /guest-post`
2. **x402 middleware** intercepts the request and displays a payment prompt
3. **User pays** the configured amount on their chosen EVM network
4. **Payment verified** on-chain via the x402 facilitator
5. **Submission stored** in D1 database with status `pending_review`
6. **Admin reviews** and updates status via the admin API

**Note**: Payment details (payer address, tx hash) are captured by the x402 middleware and currently stored as `NULL` in the database. Future versions can populate these fields for audit trails.

## Development

### Local Testing

Run the server with debug logs:
```bash
uvicorn main:app --reload --log-level debug
```

### Testing with curl

Health check:
```bash
curl http://localhost:8000/
```

List submissions (requires valid `ADMIN_TOKEN`):
```bash
curl -H "X-Admin-Token: your_token" http://localhost:8000/submissions
```

### Error Handling

- **D1 connection errors** → 502 Bad Gateway
- **Missing admin token** → 403 Forbidden
- **Submission not found** → 404 Not Found
- **Invalid input validation** → 422 Unprocessable Entity
- **Database errors after payment** → 502 with error details (payment already captured)

## Deployment

### Cloudflare Workers (Recommended)

1. Create a D1 database via `wrangler`:
   ```bash
   wrangler d1 create trovit_guest_posts
   ```

2. Initialize the schema:
   ```bash
   wrangler d1 execute trovit_guest_posts --file=schema.sql --remote
   ```

3. Deploy with Wrangler (requires a compatible wrapper or custom build)

### Traditional Server (VPS, Docker, etc.)

```bash
# Start server
uvicorn main:app --host 0.0.0.0 --port 8000

# Or with a process manager like systemd or supervisor
```

## Dependencies

See `requirements.txt`:
- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **httpx** - Async HTTP client (for D1 API calls)
- **pydantic** - Data validation
- **x402** - Cryptocurrency payment framework

## Security Considerations

- ✅ **SQL Injection Protection**: All D1 queries use parameterized statements with `?` placeholders
- ✅ **Admin Token**: Shared secret for admin endpoints (rotate regularly)
- ✅ **HTTPS Only**: Always use HTTPS in production
- ✅ **Input Validation**: Pydantic models enforce length and type constraints
- ⚠️ **Payment Finality**: Submissions are inserted *after* x402 payment settlement; if insertion fails, the payment is already captured (log and alert)

## Future Enhancements

- Store payer wallet address and transaction hash for audit trails
- Webhook notifications for approved/rejected submissions
- Rate limiting per wallet address
- Email notifications to authors
- Guest post publishing workflow
- Analytics dashboard

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source. Check the repository for license details.

## Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/BesrourMS/guest-posts-x402/issues)
- Check [x402 documentation](https://developers.cloudflare.com/api/operations/cloudflare-d1-query-database) for D1-specific questions
- Review [x402 framework docs](https://x402.org) for payment integration details

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Cloudflare D1](https://developers.cloudflare.com/d1/)
- Payment infrastructure by [x402](https://x402.org)
